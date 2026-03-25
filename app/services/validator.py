import pandas as pd

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliser les noms de colonnes"""
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.replace(r'\s+', '_', regex=True)
        .str.replace(r'[\(\)]', '', regex=True)
        .str.normalize('NFKD')
        .str.encode('ascii', errors='ignore')
        .str.decode('utf-8')
    )
    return df

def validate_numeric(df: pd.DataFrame, columns: list, allow_negative: bool = True) -> None:
    """
    Valider les colonnes numériques - DOIT s'exécuter AVANT clean_comma_numbers()
    Détecte les valeurs texte comme 'pas encore payé' dans Balance_Mars(3)
    """
    for col in columns:
        if col not in df.columns:
            continue
        
        original_values = df[col].copy()
        numeric_series = pd.to_numeric(df[col], errors='coerce')
        
        invalid_mask = numeric_series.isna() & original_values.notna()
        if invalid_mask.any():
            invalid_values = original_values.loc[invalid_mask].head(5).tolist()
            raise ValueError(
                f"La colonne '{col}' contient des valeurs non numériques: {invalid_values}. "
            )
        
        if not allow_negative and (numeric_series < 0).any():
            negative_values = original_values.loc[numeric_series < 0].head(5).tolist()
            raise ValueError(
                f"La colonne '{col}' contient des valeurs négatives: {negative_values}. "
                f"Les montants négatifs ne sont pas autorisés selon les règles métier"
            )

def validate_accounts(df: pd.DataFrame) -> None:
    """
    Valider les numéros de compte - Détecte les comptes invalides comme 'ABGD' dans Balance_Mars(1)
    """
    if "Compte" not in df.columns:
        raise ValueError("Colonne 'Compte' manquante pour la validation des comptes")
    
    invalid_accounts = []
    for idx, acc in enumerate(df["Compte"]):
        if pd.isna(acc):
            invalid_accounts.append(f"Ligne {idx+2}: Compte vide")
            continue
        
        try:
            acc_clean = str(int(float(acc)))
        except (ValueError, TypeError):
            acc_clean = str(acc).strip()
        
        if not acc_clean.isdigit() or len(acc_clean) < 2:
            invalid_accounts.append(f"Ligne {idx+2}: '{acc}' → '{acc_clean}'")
    
    if invalid_accounts:
        raise ValueError(
            f"Numéros de compte invalides (doivent être des codes numériques comme '641000'):\n" +
            "\n".join(invalid_accounts[:10])
        )