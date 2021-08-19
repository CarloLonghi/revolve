import atexit
import uuid
from concurrent.futures.process import ProcessPoolExecutor

import asyncio
from typing import AnyStr, Callable, Any, Tuple, Optional, Iterable, Union

import celery
import celery.exceptions
import math

from pyrevolve.SDF.math import Vector3
from pyrevolve.custom_logging.logger import logger
from pyrevolve.evolution.individual import Individual
from pyrevolve.evolution.population.population_config import PopulationConfig
from pyrevolve.revolve_bot import RevolveBot
from pyrevolve.tol.manage.measures import BehaviouralMeasurements
from pyrevolve.util.supervisor.rabbits import PostgreSQLDatabase
from pyrevolve.util.supervisor.rabbits import RobotState
from pyrevolve.util import Time

ISAAC_AVAILABLE = False
try:
    from pyrevolve.isaac import manage_isaac
    ISAAC_AVAILABLE = True
except Exception as e:
    assert False
    print("Could not load ISAAC simulator ", e)

app = celery.Celery('CeleryQueue', backend='rpc://', broker='pyamqp://guest@localhost//')


@app.task
def evaluate_robot(robot_sdf: AnyStr, life_timeout: float) -> int:
    """
    Evaluates robots in the gazebo CeleryWorker plugin. Behavioural data is saved in the Database
     and the ID of the robot in the database is returned.
    :param robot_sdf: SDF robot, in string
    :param life_timeout: how long should the robot be evaluated
    :return: id of the robot in the database (WARNING: may be different from robot_id)
    """
    raise NotImplementedError("Evaluating a robot is implemented in C++, inside gazebo")


@app.task
def evaluate_robot_isaac(robot_urdf: AnyStr, life_timeout: float) -> int:
    """
    Evaluates robots in isaac gym. Behavioural data is saved in the Database
     and the ID of the robot in the database is returned.
    :param robot_urdf: URDF robot, in string
    :param life_timeout: how long should the robot be evaluated
    :return: id of the robot in the database (WARNING: may be different from robot_id)
    """
    assert ISAAC_AVAILABLE
    return manage_isaac.simulator(robot_urdf, life_timeout)


def call_evaluate_robot(robot_name: AnyStr, robot_sdf: AnyStr, max_age: float, timeout: float, simulator: AnyStr) -> int:
    if simulator == 'gazebo':
        r = evaluate_robot.delay(robot_sdf, max_age)
    elif simulator == 'isaacgym':
        assert ISAAC_AVAILABLE
        r = evaluate_robot_isaac.delay(robot_sdf, max_age)
    else:
        raise RuntimeError(f"Simulator \"{simulator}\" not recognized")
    logger.info(f'Request SENT to rabbitmq: {str(r)} for "{robot_name}"')

    robot_id: int = r.get(timeout=timeout)
    logger.info(f'Request RECEIVED : {str(r)} for "{robot_name}"')
    assert(type(robot_id) is int)
    return robot_id


class CeleryQueue:
    EVALUATION_TIMEOUT = 600  # REAL SECONDS TO WAIT A RESPONSE FROM THE SIMULATOR
    MAX_ATTEMPTS = 3

    def __init__(self, args, queue_name: AnyStr = 'celery', dbname: Optional[AnyStr] = None, use_isaacgym: bool = False):
        self._queue_name: AnyStr = queue_name
        self._args = args
        self._dbname: AnyStr = str(uuid.uuid1()) if dbname is None else dbname
        self._db: PostgreSQLDatabase = PostgreSQLDatabase(dbname=self._dbname, address='localhost', username='matteo')
        self._process_pool_executor = ProcessPoolExecutor()
        self._use_isaacgym: bool = use_isaacgym
        atexit.register(
            lambda: asyncio.get_event_loop().run_until_complete(self.stop(wait=False))
        )

    async def start(self, cleanup_database=False):
        await self._db.start()
        if cleanup_database:
            self._db.destroy()
        self._db.init_db(first_time=False)

    async def stop(self, wait: Union[float, bool] = True):
        if self._db is not None:
            self._db.disconnect()
            self._db.destroy()
        self._db: Optional[PostgreSQLDatabase] = None
        if type(wait) is float:
            raise NotImplementedError("call shutdown but wait only N seconds not implemented yet")
        elif type(wait) is bool:
            self._process_pool_executor.shutdown(wait=wait, cancel_futures=True)
        else:
            raise AttributeError(f"Wait cannot be of type {type(wait)}")

    async def _call_evaluate_robot(self, robot_name: AnyStr, robot_sdf: AnyStr, max_age: float, timeout: float) -> int:
        """
        Start this task separately, hopefully this will not lock the entire process
        :param robot_name: name of the robot (for logging purposes)
        :param robot_sdf: SDF of the robots to insert
        :param max_age: how many (simulated) seconds should the individual live.
        :param timeout: how many (real) seconds to wait for a response.
        :return: robot_id in the database
        """
        loop = asyncio.get_event_loop()
        simulator = 'isaacgym' if self._use_isaacgym else 'gazebo'
        robot_id: int = await loop.run_in_executor(self._process_pool_executor,
                                                   call_evaluate_robot,
                                                   robot_name, robot_sdf, max_age, timeout, simulator)
        return robot_id

    async def test_robot(self,
                         individual: Individual,
                         robot: RevolveBot,
                         conf: PopulationConfig,
                         fitness_fun: Callable[[Any, RevolveBot], float]) \
            -> Tuple[Optional[float], Optional[BehaviouralMeasurements]]:
        """
        Sends a robot to be evaluated in the rabbitmq
        :param individual: unused
        :param robot: RevolveBot to analyze
        :param conf: configuration object with some parameters about evaluation time and grace time
        :param fitness_fun: unused
        :return: Fitness and Behaviour
        """

        for attempt in range(self.MAX_ATTEMPTS):
            pose_z: float = self._args.z_start
            if robot.simulation_boundaries is not None:
                pose_z -= robot.simulation_boundaries.min.z
            pose: Vector3 = Vector3(0.0, 0.0, pose_z)
            if self._use_isaacgym:
                robot_sdf: AnyStr = robot.to_urdf(pose)
            else:
                robot_sdf: AnyStr = robot.to_sdf(pose)
            max_age: float = conf.evaluation_time + conf.grace_time

            import xml.dom.minidom
            reparsed = xml.dom.minidom.parseString(robot_sdf)
            robot_name = ''
            for model in reparsed.documentElement.getElementsByTagName('model'):
                robot_name = model.getAttribute('name')
                if str(robot_name).isdigit():
                    error_message = f'Inserting robot with invalid name: {robot_name}'
                    logger.critical(error_message)
                    raise RuntimeError(error_message)
                logger.info(f"Inserting robot {robot_name}.")

            try:
                robot_id: int = await self._call_evaluate_robot(robot_name, robot_sdf, max_age, self.EVALUATION_TIMEOUT)
                assert(type(robot_id) == int)
            except celery.exceptions.TimeoutError:
                logger.warning(f'Giving up on robot {robot_name} after {self.EVALUATION_TIMEOUT} seconds.')
                if attempt < self.MAX_ATTEMPTS:
                    logger.warning(f'Retrying')
                continue

            # DB_ID from rabbitmq and retrieve result from database
            with self._db.session() as session:
                # behaviour = [s for s in session.query(RobotState).filter(RobotState.evaluation_robot_id == robot_id)]
                behaviour_query: Iterable[RobotState] = session\
                    .query(RobotState) \
                    .filter(RobotState.evaluation_robot_id == int(robot_id))\
                    .filter(RobotState.evaluation_n == int(99))
                first_pos: Optional[Vector3] = None
                first_time: Time
                last_pos: Optional[Vector3] = None
                last_time: Time
                for state in behaviour_query:
                    state: RobotState = state
                    last_time = Time(sec=state.time_sec, nsec=state.time_nsec)
                    last_pos = Vector3(state.pos_x, state.pos_y, state.pos_z)
                    if first_pos is None:
                        first_time = last_time
                        first_pos = last_pos.copy()

                # TODO fitness: float = fitness_fun(behaviour, robot)
                if first_pos is not None and last_pos is not None:
                    distance: Vector3 = last_pos - first_pos
                    distance_size: float = math.sqrt(distance.x*distance.x + distance.y*distance.y)
                    fitness: float = distance_size / float(last_time - first_time)
                else:
                    fitness: float = -1

            logger.info(f'Robot {robot.id} evaluation finished with fitness={fitness}')
            return fitness, BehaviouralMeasurements()

        logger.warning(f'Robot {robot.id} evaluation failed (reached max attempt of {self.MAX_ATTEMPTS}),'
                       ' fitness set to None.')
        robot_fitness_none = None
        measurements_none = None
        return robot_fitness_none, measurements_none