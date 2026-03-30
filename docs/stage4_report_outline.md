# Stage 4 Report Outline

This file is a convenience draft for the Word report from stage 4.

## 1. Topic and task description
- Topic: classification of steel surface defects.
- Goal: create a baseline neural network prototype and obtain the first recognition accuracy.

## 2. Dataset
- Source: Kaggle dataset "Defects Class and Location for Metal Surface".
- Local dataset root: `DB/`
- Stage 3 manifests: `stage3_outputs/` or `stage3_outputs_colab/`

## 3. Data parameterization
- Image size
- Batch size
- Epoch count
- Learning rate
- Weight decay
- Random seed
- Train / val / test split

## 4. Neural network architecture
- Baseline model: `ResNet18`
- Transfer learning: pretrained ImageNet weights
- Final classification head for 10 classes

## 5. Graphical confirmation
- Learning curves: loss / accuracy
- Confusion matrix
- Class-level metrics

## 6. Notebook or script
- Main training script: `scripts/stage4_baseline_train.py`
- Optional notebook: `notebooks/stage4_baseline_training_colab.ipynb`

## 7. Conclusions
- First accuracy on the test split
- Strong and weak classes
- Main limitations of the baseline

## 8. Further work plan
- Compare more architectures
- Add imbalance handling
- Improve augmentations and hyperparameters
- Prepare the final user-facing notebook for stage 5
