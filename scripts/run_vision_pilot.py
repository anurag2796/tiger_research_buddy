import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from src.processors.pdf_distiller import DeepDistiller
from rich.console import Console
from rich.progress import track
import json

console = Console()

TARGET_PDFS = [
    "a._high-order_harmonic_generation_in_helium_a_comparison_study.pdf",
    "a._opinion_dynamics_in_bounded_confidence_models_with_manipulat.pdf",
    "a._r-matrix_with_time-dependence_calculations_for_three-sideban.pdf",
    "aaron_a_multidimensional_rado_theorem.pdf",
    "aaron_a_spectral_element_method_for_meshes_with_skinny_elements.pdf",
    "aaron_nanoscale_conducting_and_insulating_domains_on_ybb_6.pdf",
    "aaron_universal_logic_with_encoded_spin_qubits_in_silicon.pdf",
    "abhinav_state-of-the-art_small_language_coder_model_mify-coder.pdf",
    "adam_exploratory_analysis_of_text_duplication_in_peer-review_reve.pdf",
    "ahmet_forecasting_cyber_attacks_with_imbalanced_data_sets_and_diff.pdf",
    "ahrash_credibility_in_second-price_auctions_an_experimental_test.pdf",
    "akhil_opus_an_integrated_assessment_model_for_satellites_and_orbit.pdf",
    "akshar_information_revolution.pdf",
    "aleena_neutrino_energy_scale_measurements_for_final_state_interacti.pdf",
    "alejandro_a_short_derivation_of_feynman_formula.pdf",
    "alejandro_democritus_as_taoist.pdf",
    "alejandro_semantic-aware_scene_recognition.pdf",
    "alessandro_one-dimensional_disordered_photonic_structures_with_two_or_m.pdf",
    "alessandro_size_effects_in_micro_and_nanoscale_materials_fracture.pdf",
    "alex_coinductive_invertibility_in_higher_categories.pdf"
]

def run_pilot():
    distiller = DeepDistiller()
    pdf_dir = Path("data/pdfs")
    output_dir = Path("data/research_cards")
    
    console.print(f"[bold blue]🚀 Starting Vision Enrichment Pilot for {len(TARGET_PDFS)} papers...[/]")
    
    success_count = 0
    domains_found = {}
    
    for filename in track(TARGET_PDFS, description="Processing Pilot Batch..."):
        pdf_path = pdf_dir / filename
        if not pdf_path.exists():
            console.print(f"[red]File not found: {filename}[/]")
            continue
            
        console.print(f"\n[cyan]Processing: {filename}[/]")
        
        # 1. Extract Text (Vision)
        text = distiller.extract_text(pdf_path)
        if not text:
            console.print(f"[red]Extraction Failed for {filename}[/]")
            continue
            
        # 2. Classify Domain
        domain = distiller.classify_domain(text)
        console.print(f"   [dim]Domain: {domain}[/]")
        domains_found[domain] = domains_found.get(domain, 0) + 1
        
        # 3. Distill (TigerCard 2.0)
        card = distiller.distill(text, filename, domain=domain)
        
        if card:
            # Save
            output_path = output_dir / f"{pdf_path.stem}_card.json"
            with open(output_path, "w") as f:
                json.dump(card, f, indent=2)
            
            kg_nodes = len(card.get('knowledge_graph', {}).get('nodes', []))
            console.print(f"   [green]✓ Success: {kg_nodes} KG Nodes extracted.[/]")
            success_count += 1
        else:
            console.print(f"   [red]✗ Distillation Failed[/]")
            
    console.print("\n[bold green]Pilot Complete![/]")
    console.print(f"Successfully Processed: {success_count}/{len(TARGET_PDFS)}")
    console.print("Domain Breakdown:")
    console.print(json.dumps(domains_found, indent=2))

if __name__ == "__main__":
    run_pilot()
