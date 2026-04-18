from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path


np = None
pd = None
Image = None
plt = None
sns = None
torch = None
nn = None
optim = None
Dataset = None
DataLoader = None
transforms = None
resnet18 = None
ResNet18_Weights = None
accuracy_score = None
classification_report = None
confusion_matrix = None
tqdm = None


REQUIRED_PACKAGES = [
    "numpy",
    "pandas",
    "Pillow",
    "matplotlib",
    "seaborn",
    "scikit-learn",
    "torch",
    "torchvision",
    "tqdm",
]


@dataclass(frozen=True)
class RunConfig:
    project_root: Path
    dataset_root: Path
    manifest_dir: Path
    output_dir: Path
    model_dir: Path
    plot_dir: Path
    report_dir: Path
    train_csv: Path
    val_csv: Path
    test_csv: Path
    image_size: int
    batch_size: int
    num_epochs: int
    learning_rate: float
    weight_decay: float
    num_workers: int
    random_seed: int
    model_name: str
    use_pretrained: bool
    device: str


class SteelDefectDataset:
    def __init__(self, dataframe, transform=None):
        self.dataframe = dataframe.reset_index(drop=True)
        self.transform = transform

    def __len__(self) -> int:
        return len(self.dataframe)

    def __getitem__(self, idx: int):
        row = self.dataframe.iloc[idx]
        image = Image.open(row["resolved_image_path"]).convert("RGB")
        target = int(row["target"])

        if self.transform is not None:
            image = self.transform(image)

        return image, target


def ensure_ml_dependencies() -> None:
    global np, pd, Image, plt, sns, torch, nn, optim, Dataset, DataLoader
    global transforms, resnet18, ResNet18_Weights, accuracy_score
    global classification_report, confusion_matrix, tqdm

    try:
        import matplotlib.pyplot as _plt
        import numpy as _np
        import pandas as _pd
        import seaborn as _sns
        import torch as _torch
        import torch.nn as _nn
        import torch.optim as _optim
        from PIL import Image as _Image
        from sklearn.metrics import accuracy_score as _accuracy_score
        from sklearn.metrics import classification_report as _classification_report
        from sklearn.metrics import confusion_matrix as _confusion_matrix
        from torch.utils.data import DataLoader as _DataLoader
        from torch.utils.data import Dataset as _Dataset
        from tqdm.auto import tqdm as _tqdm
        from torchvision import transforms as _transforms
        from torchvision.models import ResNet18_Weights as _ResNet18_Weights
        from torchvision.models import resnet18 as _resnet18
    except ImportError as exc:
        package_hint = " ".join(REQUIRED_PACKAGES)
        raise SystemExit(
            "Missing ML dependencies.\n"
            f"Install them with:\n"
            f"  python -m pip install {package_hint}\n"
            f"Details: {exc}"
        ) from exc

    np = _np
    pd = _pd
    Image = _Image
    plt = _plt
    sns = _sns
    torch = _torch
    nn = _nn
    optim = _optim
    Dataset = _Dataset
    DataLoader = _DataLoader
    transforms = _transforms
    resnet18 = _resnet18
    ResNet18_Weights = _ResNet18_Weights
    accuracy_score = _accuracy_score
    classification_report = _classification_report
    confusion_matrix = _confusion_matrix
    tqdm = _tqdm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 4 baseline training for steel defect classification."
    )
    parser.add_argument("--project-root", default=None, help="Path to the project root.")
    parser.add_argument(
        "--dataset-root",
        default=None,
        help="Path to the dataset root that contains the DB folder contents.",
    )
    parser.add_argument("--manifest-dir", default=None, help="Path to stage 3 manifests.")
    parser.add_argument("--output-dir", default=None, help="Directory for stage 4 outputs.")
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--num-epochs", type=int, default=10)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--model-name", default="resnet18")
    parser.add_argument("--device", default="auto", help='Use "auto", "cpu", or "cuda".')
    parser.add_argument(
        "--no-pretrained",
        action="store_true",
        help="Disable pretrained ImageNet weights.",
    )
    return parser.parse_args()


def detect_project_root(project_root_arg: str | None) -> Path:
    candidates = []
    if project_root_arg:
        candidates.append(Path(project_root_arg))

    repo_root = Path(__file__).resolve().parents[3]
    candidates.extend(
        [
            Path.cwd(),
            repo_root,
            Path(r"G:\Мой диск\MyProject1"),
            Path("/content/drive/MyDrive/MyProject1"),
        ]
    )

    for candidate in candidates:
        if (candidate / "DB").exists():
            return candidate.resolve()

    checked = "\n".join(f"  - {candidate}" for candidate in candidates)
    raise FileNotFoundError(
        "Could not detect the project root. Checked:\n"
        f"{checked}\n"
        'Pass it explicitly with "--project-root".'
    )


def detect_manifest_dir(project_root: Path, manifest_dir_arg: str | None) -> Path:
    candidates = []
    if manifest_dir_arg:
        candidates.append(Path(manifest_dir_arg))

    candidates.extend(
        [
            project_root / "stages" / "stage3" / "outputs",
            project_root / "stage3_outputs",
            project_root / "stage3_outputs_colab",
            project_root / "Этапы" / "stage3_outputs_colab",
        ]
    )

    for candidate in candidates:
        if (candidate / "train_manifest.csv").exists():
            return candidate.resolve()

    checked = "\n".join(f"  - {candidate}" for candidate in candidates)
    raise FileNotFoundError(
        "Could not find stage 3 manifests. Checked:\n"
        f"{checked}\n"
        'Pass them explicitly with "--manifest-dir".'
    )


def build_run_config(args: argparse.Namespace) -> RunConfig:
    project_root = detect_project_root(args.project_root)
    manifest_dir = detect_manifest_dir(project_root, args.manifest_dir)
    dataset_root = (
        Path(args.dataset_root).resolve()
        if args.dataset_root
        else (project_root / "DB").resolve()
    )
    if not dataset_root.exists():
        raise FileNotFoundError(f"Dataset root not found: {dataset_root}")

    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else (project_root / "stages" / "stage4" / "outputs").resolve()
    )
    model_dir = output_dir / "models"
    plot_dir = output_dir / "plots"
    report_dir = output_dir / "reports"

    for directory in (output_dir, model_dir, plot_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)

    device = args.device
    if device == "auto":
        ensure_ml_dependencies()
        device = "cuda" if torch.cuda.is_available() else "cpu"

    return RunConfig(
        project_root=project_root,
        dataset_root=dataset_root,
        manifest_dir=manifest_dir,
        output_dir=output_dir,
        model_dir=model_dir,
        plot_dir=plot_dir,
        report_dir=report_dir,
        train_csv=manifest_dir / "train_manifest.csv",
        val_csv=manifest_dir / "val_manifest.csv",
        test_csv=manifest_dir / "test_manifest.csv",
        image_size=args.image_size,
        batch_size=args.batch_size,
        num_epochs=args.num_epochs,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        num_workers=args.num_workers,
        random_seed=args.random_seed,
        model_name=args.model_name,
        use_pretrained=not args.no_pretrained,
        device=device,
    )


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def rebuild_image_path(image_path: str, source_folder: str, dataset_root: Path) -> str:
    image_name = Path(image_path).name
    return str(dataset_root / "images" / "images" / source_folder / image_name)


def resolve_image_path(image_path: str, source_folder: str, dataset_root: Path) -> str:
    raw_path = Path(image_path)
    if raw_path.exists():
        return str(raw_path)
    return rebuild_image_path(image_path, source_folder, dataset_root)


def load_manifest(csv_path: Path, dataset_root: Path):
    dataframe = pd.read_csv(csv_path)
    dataframe["resolved_image_path"] = dataframe.apply(
        lambda row: resolve_image_path(
            row["image_path"],
            row["source_folder"],
            dataset_root,
        ),
        axis=1,
    )
    return dataframe


def build_target_mapping(train_df):
    classes = (
        train_df[["class_id", "class_name"]]
        .drop_duplicates()
        .sort_values("class_id")
        .reset_index(drop=True)
    )

    class_id_to_target = {
        int(row.class_id): idx for idx, row in classes.iterrows()
    }
    target_to_class_name = {
        idx: row.class_name for idx, row in classes.iterrows()
    }
    target_to_class_id = {
        idx: int(row.class_id) for idx, row in classes.iterrows()
    }
    return class_id_to_target, target_to_class_name, target_to_class_id


def prepare_targets(dataframe, class_id_to_target: dict[int, int]):
    prepared = dataframe.copy()
    prepared["target"] = prepared["class_id"].map(class_id_to_target)
    return prepared


def validate_manifest_paths(dataframe, split_name: str) -> None:
    missing_paths = [
        path for path in dataframe["resolved_image_path"] if not Path(path).exists()
    ]
    if missing_paths:
        preview = "\n".join(f"  - {path}" for path in missing_paths[:10])
        raise FileNotFoundError(
            f"{split_name} has {len(missing_paths)} missing image files.\n{preview}"
        )


def build_transforms(image_size: int):
    train_transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=5),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )

    eval_transform = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )

    return train_transform, eval_transform


def create_dataloaders(
    train_df,
    val_df,
    test_df,
    image_size: int,
    batch_size: int,
    num_workers: int,
    device: str,
):
    train_transform, eval_transform = build_transforms(image_size)
    pin_memory = device.startswith("cuda")

    train_dataset = SteelDefectDataset(train_df, transform=train_transform)
    val_dataset = SteelDefectDataset(val_df, transform=eval_transform)
    test_dataset = SteelDefectDataset(test_df, transform=eval_transform)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )
    return train_loader, val_loader, test_loader


def get_model(model_name: str, num_classes: int, pretrained: bool = True):
    if model_name != "resnet18":
        raise ValueError(
            'Stage 4 baseline currently supports only model_name="resnet18".'
        )

    weights = ResNet18_Weights.DEFAULT if pretrained else None
    model = resnet18(weights=weights)
    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, num_classes)
    return model


def count_parameters(model) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def train_one_epoch(model, loader, criterion, optimizer, device: str, progress_bar=None):
    model.train()
    running_loss = 0.0
    all_targets = []
    all_preds = []

    for images, targets in loader:
        images = images.to(device)
        targets = targets.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        preds = outputs.argmax(dim=1)
        running_loss += loss.item() * images.size(0)
        all_targets.extend(targets.detach().cpu().numpy())
        all_preds.extend(preds.detach().cpu().numpy())

        if progress_bar is not None:
            progress_bar.update(1)

    epoch_loss = running_loss / len(loader.dataset)
    epoch_acc = accuracy_score(all_targets, all_preds)
    return epoch_loss, epoch_acc


def evaluate_model(model, loader, criterion, device: str, progress_bar=None):
    model.eval()
    running_loss = 0.0
    all_targets = []
    all_preds = []
    all_probs = []

    with torch.no_grad():
        for images, targets in loader:
            images = images.to(device)
            targets = targets.to(device)

            outputs = model(images)
            loss = criterion(outputs, targets)
            preds = outputs.argmax(dim=1)
            probs = torch.softmax(outputs, dim=1).max(dim=1).values

            running_loss += loss.item() * images.size(0)
            all_targets.extend(targets.detach().cpu().numpy())
            all_preds.extend(preds.detach().cpu().numpy())
            all_probs.extend(probs.detach().cpu().numpy())

            if progress_bar is not None:
                progress_bar.update(1)

    epoch_loss = running_loss / len(loader.dataset)
    epoch_acc = accuracy_score(all_targets, all_preds)
    return epoch_loss, epoch_acc, all_targets, all_preds, all_probs


def fit_model(
    model,
    train_loader,
    val_loader,
    criterion,
    optimizer,
    device: str,
    num_epochs: int,
    progress_bar=None,
):
    history_rows = []
    best_val_acc = -1.0
    best_state_dict = None

    for epoch in range(1, num_epochs + 1):
        epoch_started = time.time()
        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, device, progress_bar
        )
        val_loss, val_acc, _, _, _ = evaluate_model(
            model, val_loader, criterion, device, progress_bar
        )

        history_rows.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "train_accuracy": train_acc,
                "val_loss": val_loss,
                "val_accuracy": val_acc,
                "epoch_time_sec": time.time() - epoch_started,
            }
        )

        print(
            f"Epoch {epoch:02d}/{num_epochs}: "
            f"train_acc={train_acc:.4f}, val_acc={val_acc:.4f}"
        )

        if progress_bar is not None:
            progress_bar.set_postfix(
                epoch=f"{epoch}/{num_epochs}",
                train_acc=f"{train_acc:.3f}",
                val_acc=f"{val_acc:.3f}",
            )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state_dict = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }

    history_df = pd.DataFrame(history_rows)
    if best_state_dict is None:
        raise RuntimeError("Training did not produce a best model state.")

    model.load_state_dict(best_state_dict)
    return model, history_df, best_val_acc


def plot_history(history_df, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].plot(history_df["epoch"], history_df["train_loss"], label="train_loss")
    axes[0].plot(history_df["epoch"], history_df["val_loss"], label="val_loss")
    axes[0].set_title("Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].legend()

    axes[1].plot(
        history_df["epoch"],
        history_df["train_accuracy"],
        label="train_accuracy",
    )
    axes[1].plot(
        history_df["epoch"],
        history_df["val_accuracy"],
        label="val_accuracy",
    )
    axes[1].set_title("Accuracy")
    axes[1].set_xlabel("Epoch")
    axes[1].legend()

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_confusion_matrix(y_true, y_pred, class_names: list[str], output_path: Path) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(class_names))))

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=class_names,
        yticklabels=class_names,
        ax=ax,
    )
    ax.set_title("Confusion Matrix")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_predictions(test_df, y_true, y_pred, y_prob, target_to_class_name, output_path: Path) -> None:
    predictions_df = test_df.copy().reset_index(drop=True)
    predictions_df["true_target"] = y_true
    predictions_df["pred_target"] = y_pred
    predictions_df["pred_class_name"] = [
        target_to_class_name[int(target)] for target in y_pred
    ]
    predictions_df["pred_confidence"] = y_prob
    predictions_df.to_csv(output_path, index=False)


def build_test_metrics(
    y_true,
    y_pred,
    target_to_class_name: dict[int, str],
    target_to_class_id: dict[int, int],
    best_val_acc: float,
):
    labels = sorted(target_to_class_name.keys())
    class_names = [target_to_class_name[label] for label in labels]
    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    per_class = {}
    for label in labels:
        class_name = target_to_class_name[label]
        per_class[class_name] = {
            "target": int(label),
            "class_id": int(target_to_class_id[label]),
            "precision": float(report[class_name]["precision"]),
            "recall": float(report[class_name]["recall"]),
            "f1_score": float(report[class_name]["f1-score"]),
            "support": int(report[class_name]["support"]),
        }

    return {
        "best_val_accuracy": float(best_val_acc),
        "test_accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_avg_precision": float(report["macro avg"]["precision"]),
        "macro_avg_recall": float(report["macro avg"]["recall"]),
        "macro_avg_f1": float(report["macro avg"]["f1-score"]),
        "weighted_avg_precision": float(report["weighted avg"]["precision"]),
        "weighted_avg_recall": float(report["weighted avg"]["recall"]),
        "weighted_avg_f1": float(report["weighted avg"]["f1-score"]),
        "per_class": per_class,
    }


def save_json(payload: dict, output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def save_report_template(config: RunConfig, model_parameters: int, metrics: dict, output_path: Path) -> None:
    report_lines = [
        "# Stage 4 Report Draft",
        "",
        "## 1. Topic and task description",
        "Project topic: classification of steel surface defects.",
        "Task: train a baseline image classifier and obtain the first recognition accuracy.",
        "",
        "## 2. Dataset",
        f"- Dataset root: {config.dataset_root}",
        f"- Manifest directory: {config.manifest_dir}",
        f"- Train samples: {sum(1 for _ in config.train_csv.open('r', encoding='utf-8')) - 1}",
        f"- Val samples: {sum(1 for _ in config.val_csv.open('r', encoding='utf-8')) - 1}",
        f"- Test samples: {sum(1 for _ in config.test_csv.open('r', encoding='utf-8')) - 1}",
        "",
        "## 3. Data parameterization",
        f"- Image size: {config.image_size}",
        f"- Batch size: {config.batch_size}",
        f"- Epochs: {config.num_epochs}",
        f"- Learning rate: {config.learning_rate}",
        f"- Weight decay: {config.weight_decay}",
        f"- Random seed: {config.random_seed}",
        "",
        "## 4. Neural network architecture",
        f"- Model: {config.model_name}",
        f"- Pretrained weights: {config.use_pretrained}",
        f"- Trainable parameters: {model_parameters}",
        "",
        "## 5. Training evidence",
        f"- Accuracy plot: {config.plot_dir / 'training_history.png'}",
        f"- Confusion matrix: {config.plot_dir / 'confusion_matrix.png'}",
        f"- Test metrics JSON: {config.report_dir / 'test_metrics.json'}",
        "",
        "## 6. Code artifact",
        "- Primary script: stages/stage4/scripts/stage4_baseline_train.py",
        "",
        "## 7. Conclusions",
        f"- Best validation accuracy: {metrics['best_val_accuracy']:.4f}",
        f"- Test accuracy: {metrics['test_accuracy']:.4f}",
        f"- Macro F1: {metrics['macro_avg_f1']:.4f}",
        "",
        "## 8. Next steps",
        "- Compare several architectures instead of a single baseline.",
        "- Add class-balancing techniques because the dataset is imbalanced.",
        "- Tune augmentation, optimizer, learning rate, and epoch count.",
        "- Package the best model into a final user-friendly notebook for stage 5.",
    ]
    output_path.write_text("\n".join(report_lines), encoding="utf-8")


def run_training_pipeline(config: RunConfig) -> dict:
    set_seed(config.random_seed)

    train_df = load_manifest(config.train_csv, config.dataset_root)
    val_df = load_manifest(config.val_csv, config.dataset_root)
    test_df = load_manifest(config.test_csv, config.dataset_root)

    validate_manifest_paths(train_df, "train")
    validate_manifest_paths(val_df, "val")
    validate_manifest_paths(test_df, "test")

    class_id_to_target, target_to_class_name, target_to_class_id = build_target_mapping(train_df)
    train_df = prepare_targets(train_df, class_id_to_target)
    val_df = prepare_targets(val_df, class_id_to_target)
    test_df = prepare_targets(test_df, class_id_to_target)

    train_loader, val_loader, test_loader = create_dataloaders(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        image_size=config.image_size,
        batch_size=config.batch_size,
        num_workers=config.num_workers,
        device=config.device,
    )

    model = get_model(
        model_name=config.model_name,
        num_classes=len(class_id_to_target),
        pretrained=config.use_pretrained,
    ).to(config.device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    total_steps = (
        config.num_epochs * (len(train_loader) + len(val_loader)) + len(test_loader)
    )
    with tqdm(total=total_steps, desc="Training progress", unit="batch") as progress_bar:
        model, history_df, best_val_acc = fit_model(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            criterion=criterion,
            optimizer=optimizer,
            device=config.device,
            num_epochs=config.num_epochs,
            progress_bar=progress_bar,
        )

        test_loss, test_acc, y_true, y_pred, y_prob = evaluate_model(
            model=model,
            loader=test_loader,
            criterion=criterion,
            device=config.device,
            progress_bar=progress_bar,
        )

    metrics = build_test_metrics(
        y_true=y_true,
        y_pred=y_pred,
        target_to_class_name=target_to_class_name,
        target_to_class_id=target_to_class_id,
        best_val_acc=best_val_acc,
    )
    metrics["test_loss"] = float(test_loss)
    metrics["test_accuracy"] = float(test_acc)
    metrics["device"] = config.device
    metrics["model_name"] = config.model_name

    model_path = config.model_dir / f"{config.model_name}_best_model.pth"
    history_path = config.report_dir / "history.csv"
    metrics_path = config.report_dir / "test_metrics.json"
    class_mapping_path = config.report_dir / "class_mapping.json"
    predictions_path = config.report_dir / "test_predictions.csv"
    summary_path = config.report_dir / "run_summary.json"
    report_template_path = config.report_dir / "stage4_report_draft.md"
    history_plot_path = config.plot_dir / "training_history.png"
    confusion_matrix_path = config.plot_dir / "confusion_matrix.png"

    torch.save(model.state_dict(), model_path)
    history_df.to_csv(history_path, index=False)
    save_json(metrics, metrics_path)
    save_json(
        {
            str(target): {
                "class_id": int(target_to_class_id[target]),
                "class_name": target_to_class_name[target],
            }
            for target in sorted(target_to_class_name.keys())
        },
        class_mapping_path,
    )
    save_predictions(
        test_df=test_df,
        y_true=y_true,
        y_pred=y_pred,
        y_prob=y_prob,
        target_to_class_name=target_to_class_name,
        output_path=predictions_path,
    )

    plot_history(history_df, history_plot_path)
    plot_confusion_matrix(
        y_true=y_true,
        y_pred=y_pred,
        class_names=[target_to_class_name[idx] for idx in sorted(target_to_class_name.keys())],
        output_path=confusion_matrix_path,
    )

    model_parameters = count_parameters(model)
    summary = {
        "project_root": str(config.project_root),
        "dataset_root": str(config.dataset_root),
        "manifest_dir": str(config.manifest_dir),
        "output_dir": str(config.output_dir),
        "device": config.device,
        "model_name": config.model_name,
        "use_pretrained": config.use_pretrained,
        "image_size": config.image_size,
        "batch_size": config.batch_size,
        "num_epochs": config.num_epochs,
        "learning_rate": config.learning_rate,
        "weight_decay": config.weight_decay,
        "num_workers": config.num_workers,
        "random_seed": config.random_seed,
        "trainable_parameters": model_parameters,
        "metrics": metrics,
        "artifacts": {
            "model_path": str(model_path),
            "history_path": str(history_path),
            "metrics_path": str(metrics_path),
            "class_mapping_path": str(class_mapping_path),
            "predictions_path": str(predictions_path),
            "history_plot_path": str(history_plot_path),
            "confusion_matrix_path": str(confusion_matrix_path),
        },
    }
    save_json(summary, summary_path)
    save_report_template(config, model_parameters, metrics, report_template_path)
    return summary


def main() -> int:
    args = parse_args()
    ensure_ml_dependencies()
    config = build_run_config(args)

    print(f"Project root : {config.project_root}")
    print(f"Manifest dir : {config.manifest_dir}")
    print(f"Output dir   : {config.output_dir}")
    print(f"Device       : {config.device}")

    summary = run_training_pipeline(config)

    print("\nTraining complete.")
    print(f"Test accuracy: {summary['metrics']['test_accuracy']:.4f}")
    print(f"Macro F1     : {summary['metrics']['macro_avg_f1']:.4f}")
    print(f"Artifacts dir: {summary['output_dir']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
