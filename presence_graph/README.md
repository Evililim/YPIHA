# Presence Graph for Home Assistant

[![CI](https://github.com/example/presence_graph/actions/workflows/ci.yaml/badge.svg)](.github/workflows/ci.yaml)

## 🇬🇧 Overview

Presence Graph is a Home Assistant custom integration that estimates how many people are at home based on a graph of spaces (rooms/zones) and the sensors attached to them. The engine blends motion, presence, contact and lock events to infer traversals between rooms and to debounce false positives. Every update is explained through a dedicated event so that you can audit the reasoning in your automations.

### Key features

- Virtual model of your home as spaces and links with per-space binary sensors and global counters.
- Graph-based diffusion engine with configurable timeouts, traversal windows and anti-false-positive rules.
- Configurable entirely from the UI (Config Flow & Options Flow) with bilingual translations (EN/FR).
- Services to reload the model, force diagnostics states or toggle room inclusion in the total.
- HACS compatible structure with automated tests, typing and linting.

### Installation (HACS / manual)

1. Add the repository as a custom repository in HACS or copy the `custom_components/presence_graph` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Use *Settings → Devices & Services → Add Integration* and search for **Presence Graph**.

### Configuration workflow

1. Provide a name for the graph instance.
2. Describe your spaces (rooms/zones) with their motion/presence sensors and per-room timeout.
3. Define the links (doors/passages) with their motion, contact and lock sensors.
4. Validate the summary and create the entry. You can revisit the model from the entry options at any time.

*(Screenshot placeholders: replace with your own UI captures when available.)*

### Example automations

```yaml
alias: Turn on living room lights when occupied
trigger:
  - platform: state
    entity_id: binary_sensor.presence_graph_living
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
```

```yaml
alias: Notify when someone arrives home
trigger:
  - platform: state
    entity_id: sensor.presence_graph_total_persons
    from: "0"
    to: "1"
action:
  - service: notify.mobile_app_marie
    data:
      message: "Someone just arrived at home."
```

Use in templates:

```jinja
{{ state_attr('sensor.presence_graph_total_persons', 'occupied_spaces') | join(', ') }}
```

### Limitations & roadmap

- The current estimation assumes one person per occupied connected component. Multi-person per room heuristics are on the roadmap.
- State is not persisted across restarts (the model resets on reboot).
- Config flow expects JSON definitions for bulk editing; future versions will offer per-space wizards.

## 🇫🇷 Présentation

Presence Graph est une intégration personnalisée Home Assistant qui estime le nombre de personnes présentes à partir d’un graphe d’espaces (pièces/zones) reliés par des passages. Le moteur combine les événements des capteurs de mouvement, de présence, d’ouverture et de verrouillage pour déduire les déplacements entre pièces et filtrer les faux positifs. Chaque mise à jour s’accompagne d’un événement détaillé pour comprendre le raisonnement.

### Fonctionnalités principales

- Modèle virtuel du logement avec un binaire « occupé » par espace et des capteurs globaux de comptage.
- Moteur de diffusion sur graphe avec délais configurables, fenêtres de traversée et protections anti-faux positifs.
- Configuration complète depuis l’UI (Config Flow & Options) avec traductions FR/EN.
- Services intégrés : rechargement du modèle, forçage de l’état d’un espace, inclusion/exclusion dans le total.
- Structure compatible HACS avec tests automatisés, typage strict et linting.

### Installation (HACS / manuelle)

1. Ajoutez ce dépôt comme *Custom repository* dans HACS ou copiez le dossier `custom_components/presence_graph` dans `config/custom_components`.
2. Redémarrez Home Assistant.
3. Depuis *Paramètres → Appareils & services → Ajouter une intégration*, recherchez **Presence Graph**.

### Configuration

1. Donnez un nom à l’instance.
2. Définissez les espaces (pièces/zones) avec leurs capteurs et leurs temporisations d’occupation.
3. Déclarez les liaisons (portes/passages) avec leurs capteurs de mouvement, contact et verrou.
4. Validez le résumé ; vous pourrez éditer le graphe via les options de l’entrée.

### Automatisations d’exemple

```yaml
alias: Éteindre maison quand plus personne
trigger:
  - platform: state
    entity_id: sensor.presence_graph_total_persons
    to: "0"
    for: "00:03:00"
action:
  - service: scene.turn_on
    target:
      entity_id: scene.maison_eteinte
```

```jinja
{{ state_attr('sensor.presence_graph_total_persons','occupied_spaces') | join(', ') }}
```

### Limites connues / évolutions

- Comptage multi-personnes plus fin (par densité d’événements) à venir.
- Les états repartent de zéro après redémarrage.
- L’assistant de configuration repose pour l’instant sur l’édition JSON groupée.

## Development

- Python 3.12+, strict typing, Ruff linting and PyTest test suite.
- Run locally:

```bash
pip install -e .
pip install pytest ruff mypy
ruff check .
mypy custom_components/presence_graph
pytest
```

Contributions and feedback are welcome!
