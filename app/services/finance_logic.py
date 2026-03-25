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

def alert(variance: float) -> str:
    """
    Logique d'Alerte Fiche de Mission:
    - Écart < 0% → "vert" (Économie)
    - 0% <= Écart <= 10% → "orange" (Vigilance)
    - Écart > 10% → "rouge" (Dépassement critique)
    """
    if variance < 0:
        return "vert"
    elif variance <= 10:
        return "orange"
    else:
        return "rouge"