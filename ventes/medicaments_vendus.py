"""
Médicaments vendus : utilitaires pour les documents exportés (PDF, Excel).

- texte_medicaments(vente)  → « Amoxicilline ×2, Vermifuge ×1 »
- recap_medicaments(ventes) → [(nom, quantité totale, montant total), …]
  trié du plus vendu au moins vendu.

Les ventes doivent idéalement être chargées avec
.prefetch_related("lignes__medicament__catalogue") pour éviter une requête
par ligne.
"""

from collections import OrderedDict


def _nom(ligne):
    med = ligne.medicament
    if med is None:
        return "Médicament supprimé"
    return med.catalogue.nom if getattr(med, "catalogue", None) else str(med)


def lignes_de_la_vente(vente):
    """Liste de (nom, quantité, montant) pour une vente."""
    return [
        (_nom(l), l.quantite, float(l.montant_total or 0))
        for l in vente.lignes.all()
    ]


def texte_medicaments(vente):
    lignes = lignes_de_la_vente(vente)
    if not lignes:
        return "—"
    return ", ".join(f"{nom} ×{qte}" for nom, qte, _ in lignes)


def recap_medicaments(ventes):
    totaux = OrderedDict()
    for vente in ventes:
        for nom, qte, montant in lignes_de_la_vente(vente):
            q, m = totaux.get(nom, (0, 0.0))
            totaux[nom] = (q + qte, m + montant)
    return sorted(
        ((nom, q, m) for nom, (q, m) in totaux.items()),
        key=lambda x: (-x[1], x[0]),
    )
