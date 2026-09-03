# dataset_validation/

Dossier autonome regroupant le générateur de dataset AquaPulse, un pipeline
d'entraînement, et une suite de tests de robustesse, développés en
réaction à un problème découvert en cours de route : les premières versions
du dataset permettaient à un modèle d'obtenir de très bons scores en
s'appuyant sur des raccourcis liés à la façon dont les données étaient
générées, plutôt qu'à des patterns réalistes de fuite. Ce dossier documente
comment ce problème a été détecté, corrigé, puis vérifié.

## Contenu

| Fichier | Rôle |
|---|---|
| `generate_dataset.py` | Génère le dataset synthétique (voir section physique ci-dessous) |
| `train_model.py` | Entraîne Isolation Forest / Random Forest / Gradient Boosting, mêmes hyperparamètres que le pipeline principal |
| `validate_dataset.py` | Suite de 4 tests de robustesse (détaillés plus bas) |


## Pourquoi ce dossier existe : le problème de fond

Un modèle entraîné sur les premières versions du dataset atteignait ~92%
d'accuracy, mais deux features (`p_slope`, `pq_corr`) concentraient plus de
50% de l'importance. Un test simple a montré qu'une **règle à une seule
mesure** (par exemple "si la corrélation pression/débit est négative, c'est
une fuite") reproduisait déjà 70-78% d'accuracy à elle seule. Autrement dit,
le modèle avait surtout appris à reconnaître la façon dont le générateur
construit ses fuites (pression qui baisse pendant que le débit monte, de
façon quasi systématique), pas un pattern représentatif d'une vraie fuite
dans un réseau réel.

Deux correctifs ont été appliqués au générateur pour réduire ce problème
(détail complet dans `generate_dataset.py`, sections commentées) :
1. Augmenter et rééquilibrer la part de scénarios "ambigus" (non-fuite mais
   qui ressemblent à une fuite sur ces deux mesures)
2. Simuler une compensation partielle de pression par la régulation du
   réseau pour les petites fuites, un phénomène réaliste qui rend les
   fuites légères plus difficiles à détecter sur la seule pression

Ces correctifs améliorent la situation sans la résoudre parfaitement : c'est
un compromis assumé, pas un problème caché. C'est précisément ce que la
suite de validation ci-dessous permet de vérifier et de chiffrer.

## Troisième itération : s'inspirer de LeakDB

[LeakDB](https://github.com/KIOS-Research/LeakDB) (Vrachimis et al. 2018) est
un benchmark de référence pour la détection de fuites, construit avec
`wntr`/EPANET (simulation hydraulique de réseau complet, pas un générateur
maison). On ne reproduit pas leur approche (pas de solveur de réseau ici),
mais trois de leurs mécanismes ont été portés dans notre générateur, en
gardant l'architecture existante (Python pur, par fenêtre de capteur) :

**1. Demande multi-échelle** (inspiré de `demandGenerator.py`) : remplace le
motif horaire fixe (`HOURLY_DEMAND`, identique tous les jours) par
`hour × jour-de-semaine × bruit aléatoire` (`_demand_multiplier`). LeakDB
calibre ses coefficients de Fourier sur des données propriétaires
(`weekPat_30min.mat`) qu'on n'a pas ; on reprend seulement la structure
multi-échelle avec des paramètres choisis à la main (`WEEKDAY_FACTOR`,
`DEMAND_NOISE_STD=0.05`, même ordre de grandeur que leur `uncR`).

**2. Fuite pilotée par l'aire du trou, pas par la pression** (inspiré de
`main.py`, fonction `runScenarios`, `add_leak(area=...)`) : LeakDB fait
grandir une aire de fuite physique et laisse EPANET calculer la pression et
le débit qui en résultent. On adopte la même direction causale :
`_generate_leak_series` pilote maintenant `area_frac` (l'aire), qui alimente
la loi FAVAD déjà en place pour dériver `q_leak` et une pression cohérente,
au lieu de scripter directement la chute de pression comme avant. Deux
profils reprennent leur `leak_time_profile` :
- `abrupt` : l'aire saute à sa taille finale à l'onset et reste constante
- `incipient` : l'aire croît linéairement de 0 à sa taille finale

LeakDB tire le diamètre du trou uniformément dans [0.02, 0.2] m, sans classe
de sévérité nommée. On garde nos propres catégories minor/moderate/severe
(convention à nous, pas un standard du domaine) mais appliquées à l'aire
cible plutôt qu'à un taux de décroissance de pression arbitraire.

**3. Incertitude sur les paramètres nominaux** (inspiré de
`uncertainty_Diameter`/`uncertainty_Roughness`/`uncertainty_base_demand`) :
LeakDB randomise longueur/diamètre/rugosité de chaque conduite et la demande
de base à chaque nœud, par scénario. Sans topologie de réseau multi-tuyaux,
on applique la même idée au niveau du tuyau unique : chaque échantillon tire
`nominal_psi`/`nominal_flow` avec une déviation aléatoire de ±10%
(`_perturbed_pipe`, `PIPE_PARAM_UNCERTAINTY`) autour des valeurs
`PIPE_CONFIGS`, au lieu de réutiliser les 6 profils fixes non perturbés.

**Bug détecté et corrigé pendant cette itération** : le premier mapping
aire→pression (`exp(-diameter_factor * area_frac * 40.0)`) écrasait
`pressure_ratio` à ~0.01 pour les fuites sévères sur petit diamètre,
rendant `p_drop_pct` instable (division par une première lecture proche de
zéro, valeurs jusqu'à -12000%). Le coefficient a été réduit à `12.0`, qui
garde `pressure_ratio` dans une plage 0.3-0.9 plus plausible.

**Effet mesuré** (n=10000, seed=42) :

| Métrique | Avant (itération précédente) | Après (LeakDB-inspired) |
|---|:---:|:---:|
| Random Forest : accuracy (test) | 85% | 82% |
| Random Forest : AUC-ROC (test) | 0.936 | 0.922 |
| Règle triviale `p_slope < -0.3`   | 64% | **51%** (quasi hasard) |
| Règle triviale `pq_corr < 0`        | 71% | 75% |
| Ablation `pq_corr` seul               | -0.9 pt | **+0.3 pt** (aucune perte) |
| Ablation `pq_corr` + `p_slope`      | -2.5 pt | -0.8 pt |

Le point le plus notable : retirer `pq_corr` seul ne coûte plus rien
(auparavant -0.9 point), et retirer `pq_corr`+`p_slope` ensemble ne coûte
plus que 0.8 point contre 2.5 avant, signe que le signal est mieux
distribué. `p_slope` seul est passé de discriminant (64%) à quasiment
inutile seul (51%, proche du hasard), parce que le nouveau modèle
abrupt/incipient sur l'aire produit des pentes moins systématiquement
négatives que l'ancien modèle qui scriptait directement la pression.
`pq_corr` reste la feature la plus significative (~0.38 d'importance) et
n'est pas totalement résolu (limite ouverte, comme documenté à chaque
itération précédente).

## Les 4 tests de `validate_dataset.py`, expliqués simplement

**Test 1 : Cohérence physique (FAVAD)**
Vérifie que le matériau du tuyau influence le débit de fuite dans le bon
sens (HDPE, plus élastique, fuit davantage que la fonte, plus rigide, à
pression et diamètre égaux), conformément à la référence citée dans le
générateur (Hafsi et al. 2026, voir docstring de `_leak_coefficient_growth`
dans `generate_dataset.py`). Ce test ne juge pas la difficulté de détection,
seulement si le modèle physique se comporte comme attendu.

**Test 2 : Règles triviales à une seule mesure**
Teste si deviner juste avec un seuil sur une seule feature (`pq_corr < 0`,
`p_slope < -0.3`) approche la performance d'un vrai modèle entraîné. Si oui,
c'est un signal que le dataset est trop facilement séparable : le modèle n'a
pas grand-chose à apprendre au-delà de ce raccourci.

**Test 3 : Recouvrement des scénarios ambigus**
Pour chaque scénario "non-fuite mais suspect" (cycle de pompe, ouverture de
vanne, purge programmée, etc.), mesure combien de fois il tombe dans la même
zone de valeurs que les vraies fuites. Un scénario qui recouvre bien cette
zone aide le modèle à ne pas confondre "corrélation négative" avec "fuite
garantie".

**Test 4 : Ablation conjointe (le test le plus important)**
Entraîne le modèle en retirant les features dominantes, ensemble plutôt
qu'une par une, et regarde si la performance s'effondre ou baisse
doucement (chiffres de la version actuelle du générateur, après
l'itération LeakDB) :

| Configuration | Accuracy | AUC-ROC |
|---|:---:|:---:|
| Toutes les features | 83.5% | 0.928 |
| Sans `pq_corr` | 83.8% | 0.926 |
| Sans `p_slope` | 82.8% | 0.924 |
| Sans `pq_corr` + `p_slope` | 82.7% | 0.920 |
| Sans `pq_corr` + `p_slope` + `p_drop_pct` | 77.3% | 0.873 |

**Comment lire ce tableau** : si le modèle perdait toute sa capacité de
prédiction dès qu'on retire `pq_corr` et `p_slope`, ce serait la preuve qu'il
ne fait que reconnaître un raccourci artificiel du générateur. Ici, retirer
`pq_corr` seul ne coûte rien du tout, et retirer les deux ensemble ne fait
perdre que 0.8 point : les autres features (`p_drop_pct`, `q_surge_pct`,
`q_slope`) portent une information redondante mais réelle. Ce n'est qu'en
retirant une troisième feature que la performance chute franchement. Cette
redondance est plutôt rassurante : le modèle combine plusieurs indices qui
pointent vers la même conclusion, comme plusieurs témoins racontant la même
histoire, plutôt que de dépendre d'un indice unique et fragile.

Ce test est réutilisable au-delà de ce dataset précis : avant de présenter
la performance d'un modèle entraîné sur des données synthétiques, il vaut la
peine de vérifier si le signal est distribué (rassurant) ou concentré sur
1-2 features qui pourraient être un artefact de génération (à investiguer).