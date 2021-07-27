from __future__ import annotations

import multineat


class CppnneatGenotype:
    _multineat_genome: multineat.Genome

    def __init__(self, multineat_genome: multineat.Genome):
        self._multineat_genome = multineat_genome

    @staticmethod
    def random(
        n_inputs: int,
        n_outputs: int,
        multineat_params: multineat.Parameters,
        n_start_mutations: int,
        innov_db: multineat.InnovationDatabase,
        rng: multineat.RNG,
    ) -> CppnneatGenotype:
        multineat_genome = multineat.Genome(
            0,  # ID
            n_inputs,
            0,  # n_hidden
            n_outputs,
            False,  # FS_NEAT
            multineat.ActivationFunction.TANH,  # output activation type
            multineat.ActivationFunction.TANH,  # hidden activation type
            0,  # seed_type
            multineat_params,
            0,  # number of hidden layers
        )

        for _ in range(n_start_mutations):
            multineat_genome.Mutate(
                False,
                multineat.SearchMode.COMPLEXIFYING,
                innov_db,
                multineat_params,
                rng,
            )

        return CppnneatGenotype(multineat_genome)

    @property
    def multineat_genome(self) -> multineat.Genome:
        return self._multineat_genome

    def mutate(innov_db: multineat.InnovationDatabase, rng: multineat.RNG) -> None:
        multineat_genome.Mutate(
            False,
            multineat.SearchMode.COMPLEXIFYING,
            innov_db,
            multineat_params,
            rng,
        )
