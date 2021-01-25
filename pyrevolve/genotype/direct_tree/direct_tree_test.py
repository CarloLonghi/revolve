from pyrevolve.angle.robogen import Config
from pyrevolve.angle.robogen.spec import RobogenTreeGenerator
from pyrevolve.genotype.direct_tree.compound_mutation import DirectTreeNEATMutationConfig
from pyrevolve.genotype.direct_tree.direct_tree_config import DirectTreeMutationConfig
from pyrevolve.genotype.direct_tree.direct_tree_crossover import DirectTreeCrossoverConfig, Crossover
from pyrevolve.genotype.direct_tree.direct_tree_genotype import DirectTreeGenomeConfig, DirectTreeGenome
from pyrevolve.genotype.direct_tree.direct_tree_neat_genotype import DirectTreeNEATGenotype, \
    DirectTreeNEATGenotypeConfig
from pyrevolve.genotype.direct_tree.tree_mutation import Mutator
from pyrevolve.genotype.neat_brain_genome import NeatBrainGenomeConfig
from pyrevolve.tol.spec import get_tree_generator

config = Config(min_parts=5,
                max_parts=11,
                max_inputs=3,
                max_outputs=6,
                initial_parts_mu=8,
                initial_parts_sigma=1.5,
                disable_sensors=True,
                enable_touch_sensor=False)

robogen_tree_generator: RobogenTreeGenerator = get_tree_generator(config)

tree1 = DirectTreeGenome(config, 0)
tree2 = DirectTreeGenome(config, 1)

tree_crossover_conf = DirectTreeCrossoverConfig()
tree_crossover = Crossover(robogen_tree_generator)

brain_conf = NeatBrainGenomeConfig()
genome_config = DirectTreeNEATGenotypeConfig(config, brain_conf)

genome1 = DirectTreeNEATGenotype(genome_config, 2)
genome2 = DirectTreeNEATGenotype(genome_config, 3)

print(genome1.id, genome1._body_genome.root, genome1._body_genome.root._nodes)
print(genome2.id, genome2._body_genome.root, genome2._body_genome.root._nodes)

tree_mutation_conf = DirectTreeMutationConfig()
tree_mutation_neat_config = DirectTreeNEATMutationConfig(tree_mutation_conf, brain_conf)

mutation = Mutator(robogen_tree_generator)
genome3 = mutation.mutate(genome1, tree_mutation_neat_config, False)
genome4 = mutation.mutate(genome1, tree_mutation_neat_config, False)

print(genome3.id, genome3._body_genome.root, genome3._body_genome.root._nodes)
print(genome4.id, genome4._body_genome.root, genome4._body_genome.root._nodes)


parents = [genome1, genome2]
genome5 = tree_crossover.crossover(parents, genome_config, tree_crossover_conf)

print(genome5.id, genome5.root, genome5.root._nodes)