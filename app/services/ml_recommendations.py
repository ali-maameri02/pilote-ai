import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime

class BudgetMLRecommendations:
    """
    Système de recommandations ML pour l'analyse budgétaire
    - Prédiction de dépassement
    - Recommandations d'ajustement
    - Détection d'anomalies
    """
    
    def __init__(self):
        self.jour_actuel = datetime.now().day
        self.jours_dans_mois = 30  # Peut être dynamiqué
    
    def predict_budget_exceedance(self, data: List[Dict]) -> Dict[str, Any]:
        """
        🔮 Prédire si le budget sera dépassé en fin de mois
        Basé sur le taux de consommation actuel
        """
        predictions = []
        
        for row in data:
            budget = row.get("Montant_Prevu", 0)
            reel = row.get("Reel", 0)
            categorie = row.get("Nom_Categorie", "Inconnu")
            
            if budget <= 0:
                continue
            
            # Taux de consommation actuel
            taux_consommation = (reel / budget) * 100
            
            # Projection linéaire simple (ML léger)
            # Si on est au jour 15 et on a consommé 60%, projection = 60% * (30/15) = 120%
            facteur_projection = self.jours_dans_mois / max(self.jour_actuel, 1)
            projection_fin_mois = taux_consommation * facteur_projection
            
            # Probabilité de dépassement (logistic-like)
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
                "categorie": categorie,
                "budget": budget,
                "reel_actuel": reel,
                "taux_consommation_actuel": round(taux_consommation, 2),
                "projection_fin_mois": round(projection_fin_mois, 2),
                "probabilite_depassement": round(probabilite_depassement, 2),
                "risque": risque,
                "recommandation": self._get_exceedance_recommendation(
                    projection_fin_mois, risque, categorie
                )
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
        """
        💡 Générer des recommandations d'ajustement budgétaire
        Basé sur les écarts et patterns historiques (simulés)
        """
        recommendations = []
        
        for row in data:
            budget = row.get("Montant_Prevu", 0)
            reel = row.get("Reel", 0)
            categorie = row.get("Nom_Categorie", "Inconnu")
            ecart = row.get("Ecart_Pourcentage", 0)
            alerte = row.get("Alerte", "vert")
            
            if budget <= 0:
                continue
            
            recommandation = self._generate_category_recommendation(
                categorie, budget, reel, ecart, alerte
            )
            
            if recommandation:
                recommendations.append(recommandation)
        
        # Trier par priorité (rouge > orange > vert)
        priority_order = {"rouge": 0, "orange": 1, "vert": 2}
        recommendations.sort(key=lambda x: priority_order.get(x["priorite"], 3))
        
        return recommendations
    
    def detect_anomalies(self, balance_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        🚨 Détecter les transactions anormales (Isolation Forest simplifié)
        """
        anomalies = []
        
        if balance_data.empty:
            return anomalies
        
        # Calculer les statistiques par catégorie
        for compte in balance_data["Compte"].unique():
            compte_data = balance_data[balance_data["Compte"] == compte]
            
            for _, row in compte_data.iterrows():
                debit = row.get("Debit", 0)
                credit = row.get("Credit", 0)
                montant = max(debit, credit)
                
                # Détection d'anomalie simple (règles + statistiques)
                anomalies_detectees = []
                
                # 1. Montant inhabituellement élevé (> 2x la moyenne)
                moyenne_categorie = balance_data[balance_data["Category"] == row.get("Category", "")]["Real"].mean()
                if moyenne_categorie > 0 and montant > (moyenne_categorie * 2):
                    anomalies_detectees.append({
                        "type": "montant_eleve",
                        "description": f"Montant {montant:,.0f} DA dépasse 2x la moyenne de la catégorie",
                        "severite": "moyenne"
                    })
                
                # 2. Compte avec 0 dans les deux colonnes (oubli potentiel)
                if debit == 0 and credit == 0:
                    anomalies_detectees.append({
                        "type": "aucun_mouvement",
                        "description": "Aucun mouvement enregistré sur ce compte",
                        "severite": "faible"
                    })
                
                # 3. Ratio Débit/Crédit inhabituel pour le type de compte
                if str(compte).startswith("6") and credit > 0:
                    anomalies_detectees.append({
                        "type": "credit_inattendu",
                        "description": "Compte de charge (6xxx) avec crédit enregistré",
                        "severite": "moyenne"
                    })
                
                if str(compte).startswith("7") and debit > 0:
                    anomalies_detectees.append({
                        "type": "debit_inattendu",
                        "description": "Compte de produit (7xxx) avec débit enregistré",
                        "severite": "moyenne"
                    })
                
                if anomalies_detectees:
                    anomalies.append({
                        "compte": compte,
                        "libelle": row.get("Libelle", "Inconnu"),
                        "categorie": row.get("Category", "Inconnue"),
                        "montant": montant,
                        "anomalies": anomalies_detectees
                    })
        
        return anomalies
    
    def _get_exceedance_recommendation(self, projection: float, risque: str, categorie: str) -> str:
        """Générer recommandation basée sur la projection"""
        if risque == "élevé":
            if "Masse Salariale" in categorie:
                return "⚠️ Réduire les heures supplémentaires et reporter les recrutements"
            elif "Achats" in categorie or "Matières" in categorie:
                return "⚠️ Négocier avec fournisseurs et réduire les stocks"
            elif "Frais" in categorie:
                return "⚠️ Limiter les dépenses non essentielles et reporter les achats"
            else:
                return "⚠️ Réviser immédiatement les dépenses de cette catégorie"
        
        elif risque == "moyen":
            return "⚡ Surveiller de près et préparer un plan d'action préventif"
        
        else:
            return "✅ Bonne gestion, maintenir le cap actuel"
    
    def _generate_category_recommendation(self, categorie: str, budget: float, 
                                          reel: float, ecart: float, alerte: str) -> Dict[str, Any]:
        """Générer recommandation spécifique par catégorie"""
        
        if alerte == "rouge":
            priorite = "rouge"
            if ecart > 20:
                action = f"🔴 URGENT: Réduire les dépenses de {categorie} de {ecart-10:.0f}% pour revenir dans le budget"
            else:
                action = f"🔴 Attention: Dépassement de {ecart:.1f}%, revoir les dépenses en cours"
            
            economie_potentielle = reel - budget
            roi = "élevé"
        
        elif alerte == "orange":
            priorite = "orange"
            action = f"🟠 Vigilance: Écart de {ecart:.1f}%, surveiller les dépenses restantes"
            economie_potentielle = reel * 0.1  # 10% d'économie possible
            roi = "moyen"
        
        else:  # vert
            # Seulement recommander si économie significative (> 10%)
            if ecart < -10:
                priorite = "vert"
                action = f"🟢 Opportunité: Économie de {abs(ecart):.1f}%, possibilité de réallouer {abs(reel-budget):,.0f} DA"
                economie_potentielle = abs(reel - budget)
                roi = "faible"
            else:
                return None  # Pas de recommandation nécessaire
        
        return {
            "categorie": categorie,
            "priorite": priorite,
            "alerte": alerte,
            "action_recommandee": action,
            "budget_actuel": budget,
            "reel_actuel": reel,
            "ecart_pourcentage": round(ecart, 2),
            "economie_potentielle": round(economie_potentielle, 2),
            "roi_action": roi
        }
    
    def get_summary_insights(self, data: List[Dict], predictions: Dict) -> Dict[str, Any]:
        """
        📊 Générer des insights globaux pour le dashboard
        """
        total_budget = sum(row.get("Montant_Prevu", 0) for row in data)
        total_reel = sum(row.get("Reel", 0) for row in data)
        ecart_global = ((total_reel - total_budget) / total_budget * 100) if total_budget > 0 else 0
        
        # Catégories les plus problématiques
        categories_problematiques = sorted(
            [row for row in data if row.get("Alerte") in ["rouge", "orange"]],
            key=lambda x: x.get("Ecart_Pourcentage", 0),
            reverse=True
        )[:3]
        
        # Catégories avec meilleures performances
        categories_performantes = sorted(
            [row for row in data if row.get("Alerte") == "vert"],
            key=lambda x: x.get("Ecart_Pourcentage", 0)
        )[:3]
        
        return {
            "performance_globale": {
                "budget_total": total_budget,
                "reel_total": total_reel,
                "ecart_global_pourcentage": round(ecart_global, 2),
                "statut": "déficitaire" if ecart_global > 0 else "excédentaire"
            },
            "categories_problematiques": [
                {"nom": c.get("Nom_Categorie"), "ecart": c.get("Ecart_Pourcentage")}
                for c in categories_problematiques
            ],
            "categories_performantes": [
                {"nom": c.get("Nom_Categorie"), "economie": abs(c.get("Ecart_Pourcentage", 0))}
                for c in categories_performantes
            ],
            "recommandation_prioritaire": self._get_top_recommendation(categories_problematiques),
            "score_sante_budget": self._calculate_budget_health_score(ecart_global, predictions)
        }
    
    def _get_top_recommendation(self, categories_problematiques: List[Dict]) -> str:
        if not categories_problematiques:
            return "✅ Budget maîtrisé, continuer la bonne gestion"
        
        pire_categorie = categories_problematiques[0].get("nom", "Inconnue")
        pire_ecart = categories_problematiques[0].get("ecart", 0)
        
        return f"🎯 Priorité: Maîtriser {pire_categorie} (dépassement de {pire_ecart:.1f}%)"
    
    def _calculate_budget_health_score(self, ecart_global: float, predictions: Dict) -> int:
        """
        Calculer un score de santé budgétaire (0-100)
        """
        score = 100
        
        # Pénaliser l'écart global
        score -= min(40, abs(ecart_global) * 2)
        
        # Pénaliser les catégories à risque
        risque_eleve = predictions.get("resume", {}).get("categories_a_risque_eleve", 0)
        risque_moyen = predictions.get("resume", {}).get("categories_a_risque_moyen", 0)
        
        score -= risque_eleve * 10
        score -= risque_moyen * 5
        
        return max(0, min(100, int(score)))


# Instance globale pour réutilisation
ml_engine = BudgetMLRecommendations()