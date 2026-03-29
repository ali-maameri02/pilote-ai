import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime

class BudgetMLRecommendations:
    def __init__(self):
        self.jour_actuel = datetime.now().day
        self.jours_dans_mois = 30

    def predict_budget_exceedance(self, data: List[Dict]) -> Dict[str, Any]:
        predictions = []
        for row in data:
            budget = row.get("Montant_Prevu", 0)
            reel = row.get("Reel", 0)
            categorie = row.get("Nom_Categorie", "Inconnu")
            
            if budget <= 0: continue
            
            taux_consommation = (reel / budget) * 100
            facteur_projection = self.jours_dans_mois / max(self.jour_actuel, 1)
            projection_fin_mois = taux_consommation * facteur_projection
            
            if projection_fin_mois > 100:
                probabilite_depassement = min(99, 50 + (projection_fin_mois - 100) * 2)
                risque = "élevé"
            elif projection_fin_mois > 85:
                probabilite_depassement = 30 + (projection_fin_mois - 85) * 2
                risque = "moyen"
            else:
                probabilite_depassement = max(1, (projection_fin_mois / 100) * 30)
                risque = "faible"
            
            predictions.append({
                "categorie": categorie, "budget": budget, "reel_actuel": reel,
                "taux_consommation_actuel": round(taux_consommation, 2),
                "projection_fin_mois": round(projection_fin_mois, 2),
                "probabilite_depassement": round(probabilite_depassement, 2),
                "risque": risque,
                "recommandation": self._get_exceedance_recommendation(projection_fin_mois, risque, categorie)
            })
        
        return {
            "jour_analyse": self.jour_actuel,
            "projection_jours_restants": self.jours_dans_mois - self.jour_actuel,
            "predictions": predictions,
            "resume": {
                "categories_a_risque_eleve": sum(1 for p in predictions if p["risque"] == "élevé"),
                "categories_a_risque_moyen": sum(1 for p in predictions if p["risque"] == "moyen"),
                "categories_saines": sum(1 for p in predictions if p["risque"] == "faible")
            }
        }

    def generate_budget_recommendations(self, data: List[Dict]) -> List[Dict[str, Any]]:
        recommendations = []
        for row in data:
            budget = row.get("Montant_Prevu", 0)
            reel = row.get("Reel", 0)
            categorie = row.get("Nom_Categorie", "Inconnu")
            ecart = row.get("Ecart_Pourcentage", 0)
            alerte = row.get("Alerte", "vert")
            code_cat = row.get("Code_Categorie", "")
            
            if budget <= 0: continue
            
            rec = self._generate_category_recommendation(categorie, budget, reel, ecart, alerte, code_cat)
            if rec: recommendations.append(rec)
        
        priority_order = {"rouge": 0, "orange": 1, "vert": 2}
        recommendations.sort(key=lambda x: priority_order.get(x["priorite"], 3))
        return recommendations

    def _generate_category_recommendation(self, categorie: str, budget: float, 
                                          reel: float, ecart: float, alerte: str, code_categorie: str = "") -> Dict[str, Any]:
        is_revenue = str(code_categorie).startswith('7')
        
        if alerte == "rouge":
            priorite = "rouge"
            if is_revenue:
                action = f"🔴 URGENT: Chiffre d'affaires insuffisant (-{abs(ecart):.1f}%). Actions commerciales requises."
                economie_potentielle = 0
                roi = "élevé"
            else:
                if ecart > 20:
                    action = f"🔴 URGENT: Réduire les dépenses de {categorie} de {ecart-10:.0f}% pour revenir dans le budget"
                else:
                    action = f"🔴 Attention: Dépassement de {ecart:.1f}%, revoir les dépenses en cours"
                economie_potentielle = reel - budget
                roi = "élevé"
        
        elif alerte == "orange":
            priorite = "orange"
            if is_revenue:
                action = f"🟠 Vigilance: Objectif de vente presque atteint ({ecart:.1f}%). Accélérer les ventes."
                economie_potentielle = 0
                roi = "moyen"
            else:
                action = f"🟠 Vigilance: Écart de {ecart:.1f}%, surveiller les dépenses restantes"
                economie_potentielle = reel * 0.1
                roi = "moyen"
        
        else:  # vert
            priorite = "vert"
            if is_revenue:
                action = f"🟢 Excellente performance : +{abs(ecart):.1f}% par rapport à l'objectif !"
                economie_potentielle = 0
                roi = "faible"
            else:
                if ecart < -10:
                    action = f"🟢 Opportunité: Économie de {abs(ecart):.1f}%, possibilité de réallouer {abs(reel-budget):,.0f} DA"
                    economie_potentielle = abs(reel - budget)
                    roi = "faible"
                else:
                    return None
            
        return {
            "categorie": categorie, "priorite": priorite, "alerte": alerte,
            "action_recommandee": action, "budget_actuel": budget, "reel_actuel": reel,
            "ecart_pourcentage": round(ecart, 2), "economie_potentielle": round(economie_potentielle, 2),
            "roi_action": roi
        }

    def get_summary_insights(self, data: List[Dict], predictions: Dict) -> Dict[str, Any]:
        # Séparation Ventes (7) et Charges (6)
        total_budget_ventes = sum(r.get("Montant_Prevu", 0) for r in data if str(r.get("Code_Categorie", "")).startswith('7'))
        total_budget_charges = sum(r.get("Montant_Prevu", 0) for r in data if str(r.get("Code_Categorie", "")).startswith('6'))
        total_reel_ventes = sum(r.get("Reel", 0) for r in data if str(r.get("Code_Categorie", "")).startswith('7'))
        total_reel_charges = sum(r.get("Reel", 0) for r in data if str(r.get("Code_Categorie", "")).startswith('6'))

        resultat_net_prevu = total_budget_ventes - total_budget_charges
        resultat_net_reel = total_reel_ventes - total_reel_charges
        
        if resultat_net_prevu != 0:
            ecart_global_pourcentage = ((resultat_net_reel - resultat_net_prevu) / abs(resultat_net_prevu)) * 100
        else:
            ecart_global_pourcentage = 0 if resultat_net_reel == 0 else 100

        is_better_than_expected = resultat_net_reel > resultat_net_prevu

        categories_problematiques = sorted(
            [r for r in data if r.get("Alerte") in ["rouge", "orange"]],
            key=lambda x: x.get("Ecart_Pourcentage", 0), reverse=True
        )[:3]
        
        categories_performantes = sorted(
            [r for r in data if r.get("Alerte") == "vert"],
            key=lambda x: x.get("Ecart_Pourcentage", 0)
        )[:3]

        return {
            "performance_globale": {
                "budget_total": resultat_net_prevu,
                "reel_total": resultat_net_reel,
                "ecart_global_pourcentage": round(ecart_global_pourcentage, 2),
                "statut": "excédentaire" if is_better_than_expected else "déficitaire"
            },
            "categories_problematiques": [{"nom": c.get("Nom_Categorie"), "ecart": c.get("Ecart_Pourcentage")} for c in categories_problematiques],
            "categories_performantes": [{"nom": c.get("Nom_Categorie"), "economie": abs(c.get("Ecart_Pourcentage", 0))} for c in categories_performantes],
            "recommandation_prioritaire": self._get_top_recommendation(data),
            "score_sante_budget": self._calculate_budget_health_score(ecart_global_pourcentage, predictions)
        }

    def _get_exceedance_recommendation(self, projection: float, risque: str, categorie: str) -> str:
        if risque == "élevé":
            if "Masse Salariale" in categorie: return "⚠️ Réduire les heures supplémentaires et reporter les recrutements"
            elif "Achats" in categorie or "Matières" in categorie: return "⚠️ Négocier avec fournisseurs et réduire les stocks"
            elif "Frais" in categorie: return "⚠️ Limiter les dépenses non essentielles et reporter les achats"
            else: return "⚠️ Réviser immédiatement les dépenses de cette catégorie"
        elif risque == "moyen": return "⚡ Surveiller de près et préparer un plan d'action préventif"
        else: return "✅ Bonne gestion, maintenir le cap actuel"

    def _get_top_recommendation(self, data: List[Dict]) -> str:
        rouges = [r for r in data if r.get("Alerte") == "rouge"]
        if not rouges: return "✅ Budget maîtrisé, continuer la bonne gestion"
        pire = max(rouges, key=lambda x: x.get("Ecart_Pourcentage", 0))
        return f"🎯 Priorité: Maîtriser {pire.get('Nom_Categorie')} (dépassement de {pire.get('Ecart_Pourcentage', 0):.1f}%)"

    def _calculate_budget_health_score(self, ecart_global: float, predictions: Dict) -> int:
        score = 100
        score -= min(40, abs(ecart_global) * 2)
        score -= predictions.get("resume", {}).get("categories_a_risque_eleve", 0) * 10
        score -= predictions.get("resume", {}).get("categories_a_risque_moyen", 0) * 5
        return max(0, min(100, int(score)))

    def detect_anomalies(self, balance_data: pd.DataFrame) -> List[Dict[str, Any]]:
        anomalies = []
        if balance_data.empty: return anomalies
        for compte in balance_data["Compte"].unique():
            compte_data = balance_data[balance_data["Compte"] == compte]
            for _, row in compte_data.iterrows():
                debit = row.get("Debit", 0)
                credit = row.get("Credit", 0)
                montant = max(debit, credit)
                anomalies_detectees = []
                
                moyenne_categorie = balance_data[balance_data["Category"] == row.get("Category", "")]["Real"].mean()
                if moyenne_categorie > 0 and montant > (moyenne_categorie * 2):
                    anomalies_detectees.append({"type": "montant_eleve", "description": f"Montant {montant:,.0f} DA dépasse 2x la moyenne", "severite": "moyenne"})
                if debit == 0 and credit == 0:
                    anomalies_detectees.append({"type": "aucun_mouvement", "description": "Aucun mouvement enregistré", "severite": "faible"})
                if str(compte).startswith("6") and credit > 0:
                    anomalies_detectees.append({"type": "credit_inattendu", "description": "Compte de charge avec crédit", "severite": "moyenne"})
                if str(compte).startswith("7") and debit > 0:
                    anomalies_detectees.append({"type": "debit_inattendu", "description": "Compte de produit avec débit", "severite": "moyenne"})
                
                if anomalies_detectees:
                    anomalies.append({"compte": compte, "libelle": row.get("Libelle", "Inconnu"), "anomalies": anomalies_detectees})
        return anomalies

ml_engine = BudgetMLRecommendations()