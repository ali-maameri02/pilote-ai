import pandas as pd

def calculate_real(row) -> float:
    """
    Algorithme Fiche de Mission:
    - Compte 6xxx (Charges) → Utiliser Solde Débiteur (Debit)
    - Compte 7xxx (Produits) → Utiliser Solde Créditeur (Credit)
    """
    try:
        account = str(int(float(row["Compte"]))) if pd.notna(row["Compte"]) else ""
        debit = float(row["Debit"]) if pd.notna(row["Debit"]) else 0.0
        credit = float(row["Credit"]) if pd.notna(row["Credit"]) else 0.0
        
        if account.startswith("6"):
            return debit  # Charges = Solde Débiteur
        elif account.startswith("7"):
            return credit  # Produits = Solde Créditeur
        return 0.0
    except Exception:
        return 0.0

def compute_variance(df: pd.DataFrame) -> pd.DataFrame:
    """Écart = ((Réel - Budget) / Budget) * 100"""
    df = df.copy()
    df["Variance"] = 0.0
    
    mask = df["Montant_Prevu"] != 0
    df.loc[mask, "Variance"] = (
        (df.loc[mask, "Real"] - df.loc[mask, "Montant_Prevu"]) / 
        df.loc[mask, "Montant_Prevu"]
    ) * 100
    
    return df

def alert(variance: float, code_categorie: str = "") -> str:
    """
    Logique d'Alerte Intelligente (Fiche de Mission Adaptée):
    
    POUR LES CHARGES (Comptes 6xxx) :
    - Écart < 0% (Dépensé moins) → VERT (Économie/Bien)
    - 0% <= Écart <= 10% → ORANGE (Vigilance)
    - Écart > 10% (Dépensé plus) → ROUGE (Dépassement/Mal)

    POUR LES PRODUITS (Comptes 7xxx) :
    - Écart > 10% (Gagné plus) → VERT (Performance/Bien)
    - 0% <= Écart <= 10% → ORANGE (Vigilance)
    - Écart < 0% (Gagné moins) → ROUGE (Manque à gagner/Mal)
    """
    # Déterminer si c'est un compte de produit (7) ou charge (6)
    is_revenue = str(code_categorie).startswith("7")
    
    if is_revenue:
        # LOGIQUE REVENUS (7xxx) : Plus c'est haut, mieux c'est
        if variance > 0:
            return "vert"   # Super performance !
        elif 0 <= variance <= 10:
            return "orange" # Objectif atteint ou légèrement dépassé (Vigilance)
        else:
            return "rouge"  # On n'a pas atteint l'objectif (négatif)
    else:
        # LOGIQUE CHARGES (6xxx et autres) : Plus c'est bas, mieux c'est
        if variance < 0:
            return "vert"   # Économie réalisée
        elif 0 <= variance <= 10:
            return "orange" # Légère augmentation (Vigilance)
        else:
            return "rouge"  # Dépassement critique