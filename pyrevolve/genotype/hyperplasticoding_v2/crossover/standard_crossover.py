from pyrevolve.genotype.hyperplasticoding_v2.hyperplasticoding import HyperPlasticoding, HyperPlasticodingConfig
import neat
from pyrevolve.evolution.individual import Individual
import random
import os
from ....custom_logging.logger import genotype_logger


def standard_crossover(environments, parent_individuals, genotype_conf, crossover_conf):
    """
    Creates an child (individual) through crossover with two parents

    :param parent_genotypes: genotypes of the parents to be used for crossover
    :return: genotype result of the crossover
    """

    cppn_config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                   neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                   crossover_conf.cppn_config_path)

    first_environment = list(environments.keys())[-1]

    new_genotype = HyperPlasticoding(genotype_conf, 'tmp')

    parent_genotypes = [p[first_environment].genotype for p in parent_individuals]
    parent1 = parent_genotypes[0].cppn
    parent2 = parent_genotypes[1].cppn

    parent1.fitness = -float('Inf') if parent1.fitness is None else parent1.fitness
    parent2.fitness = -float('Inf') if parent2.fitness is None else parent2.fitness

    parent_ids = []
    crossover_attempt = random.uniform(0.0, 1.0)
    # no crossover
    if crossover_attempt > crossover_conf.crossover_prob:

        parent_ids.append(parent_genotypes[0].id)

        #TODO: replace this for simply deeply copying one random parent (not sure if would work as expected)
        new_cppn = cppn_config.genome_type(0)
        new_cppn.configure_crossover(parent1, parent1, cppn_config.genome_config)

    # do crossover
    else:

        for parent in parent_genotypes:
            parent_ids.append(parent.id)

        new_cppn = cppn_config.genome_type(0)
        new_cppn.configure_crossover(parent1, parent2, cppn_config.genome_config)

    new_genotype.cppn = new_cppn
    new_genotype.parents_ids = parent_ids
    # copy seed from one pf the parents
    # TODO: combine parents seed
    new_genotype.querying_seed = parent_genotypes[0].querying_seed


    genotype_logger.info(
        f'crossover: for genome {new_genotype.id} is done.')
    return new_genotype