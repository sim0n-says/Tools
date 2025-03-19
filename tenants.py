"""
Tenants.py

Inspiré par : Alain Duperré
Auteur : Simon Bédard
Date: 2025-03-19

Script QGIS pour attribuer des tenants à des blocs de récolte.

Ce script permet aux utilisateurs de sélectionner une couche vectorielle contenant les blocs de récolte,
de spécifier un champ identifiant le nom des blocs, et de choisir des champs supplémentaires à conserver
dans la nouvelle couche. Il calcule également la superficie de chaque bloc en hectares, la superficie
totale des tenants, et le pourcentage de superficie de chaque bloc par rapport à son tenant.

Fonctionnalités principales :
- Sélection de la couche et des champs.
- Filtrage des entités en fonction d'une expression.
- Calcul des tenants en fonction de la distance entre les blocs.
- Calculs de superficie en hectares.
- Création d'une nouvelle couche avec symbologie catégorisée par tenant.
"""

from qgis.core import *
from PyQt5.QtCore import QVariant, Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QLineEdit, QSpinBox
)

class TenantProcessorDialog(QDialog):
    def __init__(self, layers):
        super().__init__()
        self.setWindowTitle("Attribuer des Tenants")
        self.setLayout(QVBoxLayout())

        self.layers = layers

        # Sélection de la couche
        self.layer_label = QLabel("Sélectionnez la couche contenant les blocs de récolte:")
        self.layout().addWidget(self.layer_label)
        self.layer_combo = QComboBox()
        self.layer_combo.addItems([layer.name() for layer in layers])
        self.layout().addWidget(self.layer_combo)

        # Sélection du champ pour le nom du bloc
        self.field_label = QLabel("Sélectionnez le champ contenant le nom du bloc:")
        self.layout().addWidget(self.field_label)
        self.field_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self.update_fields)
        self.layout().addWidget(self.field_combo)

        # Sélection des champs supplémentaires à conserver
        self.additional_fields_label = QLabel("Sélectionnez les champs à conserver:")
        self.layout().addWidget(self.additional_fields_label)
        self.additional_fields_list = QListWidget()
        self.layout().addWidget(self.additional_fields_list)

        # Expression de filtrage
        self.expression_label = QLabel("Entrez une expression pour filtrer les entités:")
        self.layout().addWidget(self.expression_label)
        self.expression_input = QLineEdit()
        self.expression_input.setPlaceholderText("Ex: \"nom_bloc\" = 'Bloc A'")
        self.layout().addWidget(self.expression_input)

        # Distance de calcul entre les blocs
        self.distance_label = QLabel("Entrez la distance pour le calcul des tenants (en mètres):")
        self.layout().addWidget(self.distance_label)
        self.distance_spinbox = QSpinBox()
        self.distance_spinbox.setMinimum(1)
        self.distance_spinbox.setMaximum(1000)
        self.distance_spinbox.setValue(60)  # Valeur par défaut
        self.layout().addWidget(self.distance_spinbox)

        # Bouton pour exécuter le traitement
        self.process_button = QPushButton("Attribuer les Tenants")
        self.process_button.clicked.connect(self.process)
        self.layout().addWidget(self.process_button)

        self.update_fields()

    def update_fields(self):
        selected_layer_name = self.layer_combo.currentText()
        selected_layer = next(layer for layer in self.layers if layer.name() == selected_layer_name)
        fields = [field.name() for field in selected_layer.fields()]

        self.field_combo.clear()
        self.field_combo.addItems(fields)

        self.additional_fields_list.clear()
        for field in fields:
            item = QListWidgetItem(field)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.additional_fields_list.addItem(item)

    def get_selected_fields(self):
        selected_fields = []
        for index in range(self.additional_fields_list.count()):
            item = self.additional_fields_list.item(index)
            if item.checkState() == Qt.Checked:
                selected_fields.append(item.text())
        return selected_fields

    def process(self):
        selected_layer_name = self.layer_combo.currentText()
        selected_layer = next(layer for layer in self.layers if layer.name() == selected_layer_name)
        nom_bloc_field = self.field_combo.currentText()
        additional_fields = self.get_selected_fields()
        expression = self.expression_input.text()
        distance = self.distance_spinbox.value()

        if not nom_bloc_field:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un champ pour le nom du bloc.")
            return

        # Filtrer les entités en fonction de l'expression
        if expression:
            expr = QgsExpression(expression)
            request = QgsFeatureRequest(expr)
            filtered_features = [f for f in selected_layer.getFeatures(request)]
        else:
            filtered_features = selected_layer.getFeatures()

        if not filtered_features:
            QMessageBox.warning(self, "Avertissement", "Aucune entité ne correspond à l'expression de filtrage.")
            return

        # Obtenir le CRS du projet
        project_crs = QgsProject.instance().crs()

        # Créer une nouvelle couche en mémoire avec le CRS du projet
        mem_layer = QgsVectorLayer("Polygon", "Tenants", "memory")
        mem_layer.setCrs(project_crs)

        # Ajouter les champs à la nouvelle couche
        fields_to_add = [
            QgsField('tenant', QVariant.Int),
            QgsField('blocs_partages', QVariant.String),
            QgsField('id_original', QVariant.Int),
            QgsField('superficie_bloc', QVariant.Double),
            QgsField('superficie_tenant', QVariant.Double),
            QgsField('pourcentage_superficie', QVariant.Double)
        ]
        for field_name in additional_fields:
            field = selected_layer.fields().field(field_name)
            fields_to_add.append(QgsField(field.name(), field.type()))

        mem_layer.dataProvider().addAttributes(fields_to_add)
        mem_layer.updateFields()

        # Initialiser un dictionnaire pour les tenants
        tenant_dict = {}
        tenant_id = 1
        tenant_blocs = {}
        tenant_areas = {}

        # Parcourir les entités filtrées et attribuer des tenants
        for feature in filtered_features:
            geom = feature.geometry()
            if not geom or geom.isNull() or not geom.isGeosValid():
                print(f"Géométrie invalide pour l'entité ID: {feature.id()}")
                continue

            assigned = False
            nom_bloc = feature[nom_bloc_field]  # Utiliser le champ sélectionné
            bloc_area = geom.area() / 10000  # Convertir en hectares

            # Vérifier la distance minimale avec les autres blocs
            for other_feature in filtered_features:
                if other_feature.id() != feature.id():
                    other_geom = other_feature.geometry()
                    distance_between = geom.distance(other_geom)

                    if distance_between <= distance:
                        if other_feature.id() in tenant_dict:
                            tenant = tenant_dict[other_feature.id()]
                        else:
                            tenant = tenant_id
                            tenant_id += 1

                        tenant_dict[feature.id()] = tenant
                        tenant_dict[other_feature.id()] = tenant

                        # Ajouter les noms des blocs partagés
                        if tenant not in tenant_blocs:
                            tenant_blocs[tenant] = []
                        tenant_blocs[tenant].append(nom_bloc)
                        tenant_blocs[tenant].append(other_feature[nom_bloc_field])

                        # Ajouter la superficie du bloc au total du tenant
                        if tenant not in tenant_areas:
                            tenant_areas[tenant] = 0
                        tenant_areas[tenant] += bloc_area

                        assigned = True
                        break

            if not assigned:
                tenant_dict[feature.id()] = tenant_id
                tenant_id += 1
                tenant_blocs[tenant_dict[feature.id()]] = [nom_bloc]
                tenant_areas[tenant_dict[feature.id()]] = bloc_area

        # Ajouter les entités avec les champs 'tenant', 'blocs_partages', 'id_original', et les calculs de superficie à la nouvelle couche
        mem_layer.startEditing()
        for feature in filtered_features:
            tenant = tenant_dict[feature.id()]
            blocs_partages = ', '.join(set(tenant_blocs[tenant]))  # Utiliser set pour éviter les doublons
            bloc_area = feature.geometry().area() / 10000  # Convertir en hectares
            tenant_area = tenant_areas[tenant]
            pourcentage_superficie = (bloc_area / tenant_area) * 100 if tenant_area > 0 else 0

            attributes = [
                tenant,
                blocs_partages,
                feature.id(),
                bloc_area,
                tenant_area,
                pourcentage_superficie
            ]

            # Ajouter les valeurs des champs supplémentaires
            for field_name in additional_fields:
                value = feature[field_name]
                attributes.append(value if value is not None else NULL)

            new_feature = QgsFeature()
            new_feature.setGeometry(feature.geometry())
            new_feature.setAttributes(attributes)
            mem_layer.addFeature(new_feature)
        mem_layer.commitChanges()

        # Appliquer une symbologie catégorisée par tenant
        renderer = QgsCategorizedSymbolRenderer('tenant')
        renderer.setClassAttribute('tenant')
        mem_layer.setRenderer(renderer)
        mem_layer.triggerRepaint()

        # Ajouter la nouvelle couche au projet QGIS
        QgsProject.instance().addMapLayer(mem_layer)

        QMessageBox.information(self, "Succès", "Les tenants ont été attribués avec succès et la nouvelle couche 'Tenants' a été ajoutée au projet.")
        self.close()

# Exécuter le script dans QGIS
layers = [layer for layer in QgsProject.instance().mapLayers().values() if isinstance(layer, QgsVectorLayer)]
if layers:
    dialog = TenantProcessorDialog(layers)
    dialog.exec_()
else:
    QMessageBox.warning(None, "Avertissement", "Aucune couche vectorielle disponible dans le projet.")

