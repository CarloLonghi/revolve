#!/usr/bin/env python3
import asyncio
from dataclasses import dataclass

import multineat
from pyrevolve import parser
from pyrevolve.custom_logging.logger import logger
from pyrevolve.evolution import fitness
from pyrevolve.evolution.pop_management.steady_state import \
    steady_state_population_management
from pyrevolve.evolution.population import Population, PopulationConfig
from pyrevolve.evolution.selection import (multiple_selection,
                                           tournament_selection)
from pyrevolve.experiment_management import ExperimentManagement
from pyrevolve.genotype.bodybrain_composition.config import \
    BodybrainCompositionConfig
from pyrevolve.genotype.bodybrain_composition.crossover import \
    bodybrain_composition_crossover
from pyrevolve.genotype.bodybrain_composition.genotype import \
    BodybrainCompositionGenotype
from pyrevolve.genotype.bodybrain_composition.mutation import \
    bodybrain_composition_mutate
from pyrevolve.genotype.cppnneat_body.config import CppnneatBodyConfig
from pyrevolve.genotype.cppnneat_body.crossover import cppnneat_body_crossover
from pyrevolve.genotype.cppnneat_body.develop import cppnneat_body_develop
from pyrevolve.genotype.cppnneat_body.genotype import CppnneatBodyGenotype
from pyrevolve.genotype.cppnneat_body.mutation import cppnneat_body_mutate
from pyrevolve.genotype.cppnneat_cpg_brain.config import CppnneatCpgBrainConfig
from pyrevolve.genotype.cppnneat_cpg_brain.crossover import \
    cppnneat_cpg_brain_crossover
from pyrevolve.genotype.cppnneat_cpg_brain.develop import \
    cppnneat_cpg_brain_develop
from pyrevolve.genotype.cppnneat_cpg_brain.genotype import \
    CppnneatCpgBrainGenotype
from pyrevolve.genotype.cppnneat_cpg_brain.mutation import \
    cppnneat_cpg_brain_mutate
from pyrevolve.util.supervisor.analyzer_queue import AnalyzerQueue
from pyrevolve.util.supervisor.simulator_queue import SimulatorQueue


@dataclass
class GenotypeConstructorConfig:
    body_n_start_mutations: int
    brain_n_start_mutations: int
    bodybrain_composition_config: BodybrainCompositionConfig
    body_multineat_params: multineat.Parameters
    brain_multineat_params: multineat.Parameters


def create_random_genotype(
    config: GenotypeConstructorConfig, id: int
) -> BodybrainCompositionGenotype:
    return BodybrainCompositionGenotype(
        id,
        config.bodybrain_composition_config,
        CppnneatBodyGenotype.random(
            config.body_multineat_params,
            config.body_n_start_mutations,
            config.bodybrain_composition_config.body_develop_config.innov_db,
            config.bodybrain_composition_config.body_develop_config.rng,
        ),
        CppnneatCpgBrainGenotype.random(
            config.brain_multineat_params,
            config.brain_n_start_mutations,
            config.bodybrain_composition_config.brain_develop_config.innov_db,
            config.bodybrain_composition_config.brain_develop_config.rng,
        ),
    )


async def run():
    """
    The main coroutine, which is started below.
    """

    # experiment settings
    num_generations = 3
    population_size = 30
    offspring_size = 15

    body_n_start_mutations: int = 10
    brain_n_start_mutations: int = 10

    # multineat rng
    rng = multineat.RNG()
    rng.TimeSeed()

    # multineat innovation database
    innov_db = multineat.InnovationDatabase()

    # config for body
    body_config = CppnneatBodyConfig(innov_db, rng)

    # config for brain
    brain_config = CppnneatCpgBrainConfig(
        innov_db,
        rng,
        abs_output_bound=1.0,  # maximum(and minimum, negative) ceiling of actuator position. 1 is the value we want for gazebo and our real robots
        use_frame_of_reference=False,  # at some point we will use this for directed locomation(use emiels stuff)
        signal_factor_all=4.0,  # actuator gain
        signal_factor_mid=2.5,  # not used anymore after update later(see emiels code)
        signal_factor_left_right=2.5,  # not used anymore after update later(see emiels code)
        range_ub=1.0,  # scales weights to be between -1 and 1. Our weights are between 0 and 1 so this value is good.
        init_neuron_state=0.707,  # x to this value and y to minus this
        reset_neuron_random=False
    )

    # body multineat settings
    body_multineat_params = multineat.Parameters()

    body_multineat_params.MutateRemLinkProb = 0.02
    body_multineat_params.RecurrentProb = 0.0
    body_multineat_params.OverallMutationRate = 0.15
    body_multineat_params.MutateAddLinkProb = 0.08
    body_multineat_params.MutateAddNeuronProb = 0.01
    body_multineat_params.MutateWeightsProb = 0.90
    body_multineat_params.MaxWeight = 8.0
    body_multineat_params.WeightMutationMaxPower = 0.2
    body_multineat_params.WeightReplacementMaxPower = 1.0
    body_multineat_params.MutateActivationAProb = 0.0
    body_multineat_params.ActivationAMutationMaxPower = 0.5
    body_multineat_params.MinActivationA = 0.05
    body_multineat_params.MaxActivationA = 6.0

    body_multineat_params.MutateNeuronActivationTypeProb = 0.03

    body_multineat_params.ActivationFunction_SignedSigmoid_Prob = 0.0
    body_multineat_params.ActivationFunction_UnsignedSigmoid_Prob = 0.0
    body_multineat_params.ActivationFunction_Tanh_Prob = 1.0
    body_multineat_params.ActivationFunction_TanhCubic_Prob = 0.0
    body_multineat_params.ActivationFunction_SignedStep_Prob = 1.0
    body_multineat_params.ActivationFunction_UnsignedStep_Prob = 0.0
    body_multineat_params.ActivationFunction_SignedGauss_Prob = 1.0
    body_multineat_params.ActivationFunction_UnsignedGauss_Prob = 0.0
    body_multineat_params.ActivationFunction_Abs_Prob = 0.0
    body_multineat_params.ActivationFunction_SignedSine_Prob = 1.0
    body_multineat_params.ActivationFunction_UnsignedSine_Prob = 0.0
    body_multineat_params.ActivationFunction_Linear_Prob = 1.0

    body_multineat_params.MutateNeuronTraitsProb = 0.0
    body_multineat_params.MutateLinkTraitsProb = 0.0

    body_multineat_params.AllowLoops = False

    # brain multineat settings
    brain_multineat_params = multineat.Parameters()

    brain_multineat_params.MutateRemLinkProb = 0.02
    brain_multineat_params.RecurrentProb = 0.0
    brain_multineat_params.OverallMutationRate = 0.15
    brain_multineat_params.MutateAddLinkProb = 0.08
    brain_multineat_params.MutateAddNeuronProb = 0.01
    brain_multineat_params.MutateWeightsProb = 0.90
    brain_multineat_params.MaxWeight = 8.0
    brain_multineat_params.WeightMutationMaxPower = 0.2
    brain_multineat_params.WeightReplacementMaxPower = 1.0
    brain_multineat_params.MutateActivationAProb = 0.0
    brain_multineat_params.ActivationAMutationMaxPower = 0.5
    brain_multineat_params.MinActivationA = 0.05
    brain_multineat_params.MaxActivationA = 6.0

    brain_multineat_params.MutateNeuronActivationTypeProb = 0.03

    brain_multineat_params.ActivationFunction_SignedSigmoid_Prob = 0.0
    brain_multineat_params.ActivationFunction_UnsignedSigmoid_Prob = 0.0
    brain_multineat_params.ActivationFunction_Tanh_Prob = 1.0
    brain_multineat_params.ActivationFunction_TanhCubic_Prob = 0.0
    brain_multineat_params.ActivationFunction_SignedStep_Prob = 1.0
    brain_multineat_params.ActivationFunction_UnsignedStep_Prob = 0.0
    brain_multineat_params.ActivationFunction_SignedGauss_Prob = 1.0
    brain_multineat_params.ActivationFunction_UnsignedGauss_Prob = 0.0
    brain_multineat_params.ActivationFunction_Abs_Prob = 0.0
    brain_multineat_params.ActivationFunction_SignedSine_Prob = 1.0
    brain_multineat_params.ActivationFunction_UnsignedSine_Prob = 0.0
    brain_multineat_params.ActivationFunction_Linear_Prob = 1.0

    brain_multineat_params.MutateNeuronTraitsProb = 0.0
    brain_multineat_params.MutateLinkTraitsProb = 0.0

    brain_multineat_params.AllowLoops = False

    # bodybrain composition genotype config
    bodybrain_composition_config = BodybrainCompositionConfig(
        body_crossover=cppnneat_body_crossover,
        brain_crossover=cppnneat_cpg_brain_crossover,
        body_crossover_config=body_config,
        brain_crossover_config=brain_config,
        body_mutate=cppnneat_body_mutate,
        brain_mutate=cppnneat_cpg_brain_mutate,
        body_mutate_config=body_config,
        brain_mutate_config=brain_config,
        body_develop=cppnneat_body_develop,
        brain_develop=cppnneat_cpg_brain_develop,
        body_develop_config=body_config,
        brain_develop_config=brain_config,
    )

    # genotype constructor config. Used by `create_random_genotype` in this file.
    genotype_constructor_config = GenotypeConstructorConfig(
        body_n_start_mutations,
        brain_n_start_mutations,
        bodybrain_composition_config,
        body_multineat_params,
        brain_multineat_params,
    )

    ###### From here on I did not check things yet --Aart

    # Parse command line / file input arguments
    settings = parser.parse_args()
    experiment_management = ExperimentManagement(settings)
    do_recovery = (
        settings.recovery_enabled and not experiment_management.experiment_is_new()
    )

    logger.info(
        "Activated run " + settings.run + " of experiment " + settings.experiment_name
    )

    if do_recovery:
        (
            gen_num,
            has_offspring,
            next_robot_id,
        ) = experiment_management.read_recovery_state(population_size, offspring_size)

        if gen_num == num_generations - 1:
            logger.info("Experiment is already complete.")
            return
    else:
        gen_num = 0
        next_robot_id = 1

    population_conf = PopulationConfig(
        population_size=population_size,
        genotype_constructor=create_random_genotype,
        genotype_conf=genotype_constructor_config,
        fitness_function=fitness.displacement_velocity,
        mutation_operator=bodybrain_composition_mutate,
        mutation_conf=bodybrain_composition_config,
        crossover_operator=bodybrain_composition_crossover,
        crossover_conf=bodybrain_composition_config,
        selection=lambda individuals: tournament_selection(individuals, 2),
        parent_selection=lambda individuals: multiple_selection(
            individuals, 2, tournament_selection
        ),
        population_management=steady_state_population_management,
        population_management_selector=tournament_selection,
        evaluation_time=settings.evaluation_time,
        offspring_size=offspring_size,
        experiment_name=settings.experiment_name,
        experiment_management=experiment_management,
    )

    n_cores = settings.n_cores

    simulator_queue = SimulatorQueue(n_cores, settings, settings.port_start)
    await simulator_queue.start()

    analyzer_queue = None  # AnalyzerQueue(1, settings, settings.port_start + n_cores)
    # await analyzer_queue.start()

    population = Population(
        population_conf, simulator_queue, analyzer_queue, next_robot_id
    )

    if do_recovery:
        # loading a previous state of the experiment
        await population.load_snapshot(gen_num)
        if gen_num >= 0:
            logger.info(
                "Recovered snapshot "
                + str(gen_num)
                + ", pop with "
                + str(len(population.individuals))
                + " individuals"
            )
        if has_offspring:
            individuals = await population.load_offspring(
                gen_num, population_size, offspring_size, next_robot_id
            )
            gen_num += 1
            logger.info("Recovered unfinished offspring " + str(gen_num))

            if gen_num == 0:
                await population.init_pop(individuals)
            else:
                population = await population.next_gen(gen_num, individuals)

            experiment_management.export_snapshots(population.individuals, gen_num)
    else:
        # starting a new experiment
        experiment_management.create_exp_folders()
        await population.init_pop()
        experiment_management.export_snapshots(population.individuals, gen_num)

    while gen_num < num_generations - 1:
        gen_num += 1
        population = await population.next_gen(gen_num)
        experiment_management.export_snapshots(population.individuals, gen_num)

    # output result after completing all generations...