from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import traceback

from app.services.validator import normalize_columns, validate_numeric, validate_accounts
from app.services.finance_logic import calculate_real, compute_variance, alert
from app.services.ml_recommendations import ml_engine
from app.models.responses import success_response, error_response

app = FastAPI(title="Smart Import Budget API", description="Système de comparaison financière Excel avec IA", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def home(): return {"message": "API Smart Budget v3.0 - Résultat Net Actif"}

@app.get("/ml/info")
def ml_info():
    return {"statut": "actif", "fonctionnalites": ["Prédiction", "Recommandations Intelligentes", "Détection Anomalies", "Score Santé"]}

def clean_comma_numbers(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

@app.post("/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
        return error_response("Format de fichier invalide.")

    try:
        contents = await file.read()
        excel_file = pd.ExcelFile(io.BytesIO(contents))
        sheet_names = excel_file.sheet_names
        print(f"📋 Onglets détectés : {sheet_names}")

        budget_sheet_name = None
        balance_sheets = []

        for sheet in sheet_names:
            df_header = pd.read_excel(excel_file, sheet_name=sheet, nrows=0)
            cols = [str(c).lower().strip() for c in df_header.columns]
            cols_text = " ".join(cols)

            is_budget_name = "budget" in sheet.lower()
            is_budget_content = ("code" in cols_text or "cat" in cols_text) and ("montant" in cols_text or "prevu" in cols_text)
            
            if (is_budget_name or is_budget_content) and "erreur" not in sheet.lower():
                if budget_sheet_name is None:
                    budget_sheet_name = sheet
                    print(f"✅ Budget identifié : '{sheet}'")
                continue

            has_compte = "compte" in cols_text
            has_debit = any(k in cols_text for k in ["debit", "débiteur", "debiteur", "depense"])
            has_credit = any(k in cols_text for k in ["credit", "créditeur", "crediteur", "revenu"])
            
            if has_compte and has_debit and has_credit and "erreur" not in sheet.lower():
                balance_sheets.append(sheet)
                print(f"✅ Balance identifiée : '{sheet}'")

        if not budget_sheet_name:
            return error_response(f"❌ Aucun onglet 'Budget' trouvé. Onglets : {', '.join(sheet_names)}")
        if not balance_sheets:
            return error_response(f"❌ Aucun onglet 'Balance' trouvé. Onglets : {', '.join(sheet_names)}")

        budget = pd.read_excel(excel_file, sheet_name=budget_sheet_name)
        budget = budget.rename(columns={"Code_Cat": "Code_Categorie", "Montant_Prevu (DA)": "Montant_Prevu", "Nom_Categorie": "Nom_Categorie"})
        budget = normalize_columns(budget)
        budget = clean_comma_numbers(budget, ["Montant_Prevu"])

        if not all(c in budget.columns for c in ["Code_Categorie", "Nom_Categorie", "Montant_Prevu"]):
            return error_response(f"❌ Budget incomplet. Manque : {[c for c in ['Code_Categorie', 'Nom_Categorie', 'Montant_Prevu'] if c not in budget.columns]}")

        budget["Code_Categorie"] = budget["Code_Categorie"].astype(str).str.zfill(2)

        all_results = []
        summary = {"total_onglets_traites": 0, "onglets_succes": 0, "onglets_echec": 0, "details_onglets": []}

        for balance_sheet_name in balance_sheets:
            print(f"\n🔄 Traitement : {balance_sheet_name}")
            sheet_result = {"nom_onglet": balance_sheet_name, "statut": "en_attente", "donnees": None, "erreur": None, "ml_recommendations": None}

            try:
                balance = pd.read_excel(excel_file, sheet_name=balance_sheet_name)
                balance = balance.rename(columns={
                    "Solde Débiteur (Dépenses)": "Debit", "Solde Debiteur (Dépenses)": "Debit",
                    "Solde Créditeur (Revenus)": "Credit", "Solde Crediteur (Revenus)": "Credit",
                    "Libellé du compte": "Libelle", "Libelle du compte": "Libelle",
                    "Compte": "Compte", "Debit": "Debit", "Credit": "Credit", "Libelle": "Libelle"
                })
                balance = normalize_columns(balance)

                if not all(c in balance.columns for c in ["Compte", "Libelle", "Debit", "Credit"]):
                    raise ValueError(f"Colonnes introuvables : {list(balance.columns)}")

                validate_numeric(balance, ["Debit", "Credit"], allow_negative=False)
                validate_accounts(balance)
                balance = clean_comma_numbers(balance, ["Debit", "Credit"])

                balance["Compte"] = balance["Compte"].astype(str).str.strip()
                balance["Real"] = balance.apply(calculate_real, axis=1)
                balance["Category"] = balance["Compte"].str[:2].str.zfill(2)
                
                real_by_category = balance.groupby("Category")["Real"].sum().reset_index()
                result = budget.merge(real_by_category, left_on="Code_Categorie", right_on="Category", how="left")
                result["Real"] = result["Real"].fillna(0)
                result = compute_variance(result)
                result["Alert"] = result.apply(lambda row: alert(row["Variance"], row["Code_Categorie"]), axis=1)

                clean_result = result.where(pd.notnull(result), None).to_dict(orient="records")
                french_clean_result = [
                    {"Code_Categorie": r.get("Code_Categorie"), "Nom_Categorie": r.get("Nom_Categorie"),
                     "Montant_Prevu": r.get("Montant_Prevu"), "Reel": r.get("Real"),
                     "Ecart_Pourcentage": r.get("Variance"), "Alerte": r.get("Alert")} 
                    for r in clean_result
                ]

                # IA / ML
                predictions = ml_engine.predict_budget_exceedance(french_clean_result)
                
                # Génération manuelle des recommandations pour passer le Code_Categorie
                recommendations = []
                for row in french_clean_result:
                    rec = ml_engine._generate_category_recommendation(
                        row["Nom_Categorie"], row["Montant_Prevu"], row["Reel"], 
                        row["Ecart_Pourcentage"], row["Alerte"], row["Code_Categorie"]
                    )
                    if rec: recommendations.append(rec)
                
                anomalies = ml_engine.detect_anomalies(balance)
                insights = ml_engine.get_summary_insights(french_clean_result, predictions)

                sheet_result["statut"] = "succes"
                sheet_result["donnees"] = french_clean_result
                sheet_result["ml_recommendations"] = {
                    "predictions_depassement": predictions, 
                    "recommandations_budgetaires": recommendations,
                    "anomalies_detectees": anomalies, 
                    "insights_globaux": insights
                }
                sheet_result["resume"] = {
                    "total_categories": len(french_clean_result),
                    "total_reel": sum(r.get("Reel", 0) for r in french_clean_result),
                    "total_budget": sum(r.get("Montant_Prevu", 0) for r in french_clean_result),
                    "alertes": {"vert": sum(1 for r in french_clean_result if r.get("Alerte") == "vert"),
                                "orange": sum(1 for r in french_clean_result if r.get("Alerte") == "orange"),
                                "rouge": sum(1 for r in french_clean_result if r.get("Alerte") == "rouge")}
                }
                summary["onglets_succes"] += 1

            except ValueError as ve:
                sheet_result["statut"] = "erreur"
                sheet_result["erreur"] = f"Erreur de validation: {str(ve)}"
                summary["onglets_echec"] += 1
            except Exception as e:
                sheet_result["statut"] = "erreur"
                sheet_result["erreur"] = f"Erreur serveur: {type(e).__name__} - {str(e)}"
                summary["onglets_echec"] += 1

            all_results.append(sheet_result)
            summary["details_onglets"].append({"nom_onglet": balance_sheet_name, "statut": sheet_result["statut"]})
            summary["total_onglets_traites"] += 1

        return success_response({"resume_fichier": summary, "resultats_onglets": all_results})

    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ Globale: {tb}")
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Erreur serveur: {str(e)}", "traceback": tb})

# This is important for Vercel
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
