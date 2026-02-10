## Neutrino energy scale measurements for final state interactions using advanced computing in DUNE

### Aleena Rafique

Argonne National Laboratory

### for the DUNE collaboration

The Deep Underground neutrino experiment (DUNE) [\[1\]](#page-5-0), consisting of near (DUNE-ND) [\[2\]](#page-5-1) and far (DUNE-FD) [\[3\]](#page-5-2) detectors, is a long-baseline experiment that is designed to measure neutrino oscillations, as well as searches beyond the standard model. The DUNE-FD will operate with an active volume of 40 kiloton liquid argon and will be situated at Sanford Underground Research Facility (SURF) in South Dakota. The DUNE-ND will be placed close to the neutrino source and measure an un-oscillated neutrino beam for precise measurement of oscillation parameters. Final State Interactions (FSI) are the secondary interactions of the daughter particles of the neutrino with other nucleons within the same argon nucleus. We present the impact of using different final state interaction models on the neutrino energy scale measurements in DUNE using advanced computing at Argonne National Laboratory.

#### PRESENTED AT

NuPhys2023, Prospects in Neutrino Physics King's College, London, UK, December 18–20, 2023

## 1 Introduction

## 1.1 DUNE

DUNE is a next-generation, long-baseline (1300 km) neutrino oscillation experiment which will carry out a detailed study of neutrino mixing utilizing high-intensity ν<sup>µ</sup> and ν<sup>µ</sup> beams measured over a long baseline. DUNE consists of an FD having 40 kiloton active mass liquid argon time projection chamber (LArTPC) at Sanford Underground Research Facility (SURF) located in South Dakota, and an ND that will be situated at Fermilab. DUNE will measure neutrino oscillation probability to determine mass ordering and charge-parity violation phase via ν<sup>e</sup> appearance and ν<sup>µ</sup> disappearance. DUNE will also carry out a rich program of the search for BSM physics and supernova neutrinos.

The studies presented in this document focus on DUNE-FD. The DUNE-FD consists of four LArTPC modules each having a fiducial mass of 10 kiloton placed at SURF. One of these module is a horizontal-drift LArTPC; the other will be a vertical-drift TPC. The technology R&D for the 3rd and 4th module technology is ongoing.

<span id="page-1-0"></span>Figure [1](#page-1-0) (left) presents the DUNE experiment schematic; and Figure [1](#page-1-0) (right) presents the DUNE-FD site at SURF with a cavern for four TPCs.

![](_page_1_Figure_5.jpeg)

Figure 1: The DUNE experiment schematic showing the near and far detectors at Fermilab and SURF respectively [\[3\]](#page-5-2) (left); the DUNE FD site [\[3\]](#page-5-2) (right).

## 1.2 Argonne Computing Resources

The generation and management of the scientific datasets are central to achieving the scientific objectives of DUNE. The DUNE detectors are expected to collect several terabytes of data every second, a volume that presents significant computational challenges. Our work on the Argonne Supercomputing resources focuses on producing the neutrino detector simulation data for physics analysis. In this paper we present results on the effects of final state interactions in the initial event generation stage, which generates several gigabytes of data and consumes hundreds of CPU and GPU combined hours per production. We will also extending this effort to include detector simulation which is substantially more CPU intensive. The goals include scaling down the simulation time and adapting the data storage methods for efficient I/O on HPC systems. Argonne has two computing facilities, namely Argonne Leadership Computing Facility (ALCF) and Laboratory Computing Resource Center (LCRC). Figure [2](#page-2-0) presents a list and description of all the available computing resources present at these facilities. We have been using bebop and swing machines for the work presented here in this document.

<span id="page-2-0"></span>

| Resources      | Description                                                                                |          |                                         |
|----------------|--------------------------------------------------------------------------------------------|----------|-----------------------------------------|
| Theta          | 11.7-petaflops supercomputer based on Intel processors                                     |          |                                         |
| ThetaGPU       | NVIDIA DGX A100 Tensor Core GPUs                                                           | Восония  | Description                             |
| ANL AI-Testbed | Machine learning based high-<br>performance computing applications                         | Resource | Description                             |
| Polaris        | 44-petaflop peak performance<br>CPU/GPU, platform to test and optimize<br>codes for Aurora | Bebop    | Intel Xenon CPUs with 1024 public nodes |
| Aurora         | ANL's first exasclae supercomputer, projected peak performance of 2 exaflops               | Swing    | NVIDIA AI100 GPUs with 6 public nodes   |

Figure 2: Description of the resources present at ALCF (left); at LCRC (right).

## 1.3 Final State Interactions

When a neutrino interacts with an argon nucleus, the initial state particles are produced. The initial state hadrons undergo secondary interactions, called the final state interactions (FSI), with other nucleons present within the same nucleus. Figure [3](#page-3-0) (left) presents an illustration of FSIs, in which a proton (light-blue line) undergo various types of hadronic FSIs [\[4\]](#page-5-3).

FSI present an important way to mask the identity of the primary interaction and can change the topology of the interaction and can also impact the final state energy. FSI are dominant in heavier nuclei such as argon. Figure [3](#page-3-0) (right) presents how initially a three-particle topology neutrino interaction can be changed into a two-particle topology and vice versa.

## 2 Sample Generation and Workflow

5k events were generated using GENIE (version 3.4 AR23 20i) [\[5\]](#page-5-4) standalone neutrino event generator using ANL computing resources. Each same initial state interaction was then propagated to the following FSI models.

<span id="page-3-0"></span>![](_page_3_Picture_0.jpeg)

Figure 3: Figure from [\[4\]](#page-5-3) illustrating the FSIs (left); FSI changing the topologies of the interaction (right).

- hA: the default model used in most current neutrino simulations. It only considers one hadron rescattering.
- hN: it considers multiple rescatterings until the hadron escape the nucleus.
- INCL++: the entire hadron-residual system changes through time steps.
- Geant4: Bertini Cascades (G4BC) [\[6\]](#page-5-5), more sophisticated model.

As a result of this, four samples were generated. The impact on the final state energies is presented in this document.

# 3 Observations and Results

The sum of all the initial and final state energies is calculated by

$$E_{i/f} = E_h + E_l - E_n \tag{1}$$

where E<sup>i</sup> or E<sup>f</sup> is the sum of the initial state (before FSI) or final state (after FSI) particle energies respectively; E<sup>h</sup> is the initial or final state hadronic energy sum; E<sup>l</sup> is the primary lepton energy; and E<sup>n</sup> is the hit nucleon energy. The sum is over all the particles of an interaction. This energy spectrum is presented in Figure [4](#page-4-0) (left) for initial state and (right) for final state energy sum for all FSIs. We see that the initial state energies are consistent across all four FSIs as expected. We also see that there is a discrepancy in final state energy sum from the default tune (hA) as large as 45%. These discrepancies limit our model understanding and will impact the energy scale and reconstruction.

Figure [5](#page-4-1) presents the initial versus final state energies for different FSI models. There seems to be a better agreement in initial and final state energies for the models hN and INCL++ compared to the default hA model.

<span id="page-4-0"></span>![](_page_4_Figure_0.jpeg)

<span id="page-4-1"></span>Figure 4: Energy sum of the initial state particles (left); Energy sum of the final state particles (right).

![](_page_4_Figure_2.jpeg)

Figure 5: Initial versus final state energy sum for hA (top left); hN (top right); INCL++ (bottom left); and Geant4 (bottom right).

# 4 Conclusions and Outlook

This is the first demonstration of utilizing Argonne computing for DUNE physics studies. We observed how FSI can impact the neutrino energy spectrum. In future, we plan to look into the dependence of the energy difference between different neutrino interaction types (QE, RES, DIS etc). We also plan to reconstruct the neutrino energy using FD reconstruction tools. In addition, we will calculate the effect of these uncertainties on the CP violation sensitivity studies.

## References

- <span id="page-5-0"></span>[1] B. Abi et al. [DUNE Collaboration], EPJC 80 978 (2020).
- <span id="page-5-1"></span>[2] A. Abed Abud et al. [DUNE Collaboration], Instruments 2021, 5(4), 31 (2021).
- <span id="page-5-2"></span>[3] B. Abi et al. [DUNE Collaboration], JINST 15, no. 08, T08008 (2020).
- <span id="page-5-3"></span>[4] L. Bathe-Peters et al., <https://arxiv.org/pdf/2201.04664.pdf>.
- <span id="page-5-4"></span>[5] C. Andreopoulos et al., <https://arxiv.org/pdf/1510.05494.pdf>.
- <span id="page-5-5"></span>[6] D. H. Wright et al., Nuclear. Ins. Meth. Phys. Res A 804 (2015) 175-188.