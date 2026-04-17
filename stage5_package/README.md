# Stage 5 Package

В этой папке собраны файлы для этапа 5.

Состав папки:

- `stage5_experiments_colab.ipynb` — ноутбук для экспериментов с обучением модели.
- `stage5_final_inference_colab.ipynb` — финальный ноутбук для использования готовой модели.
- `resnet18_best_model.pth` — веса лучшей модели по обновлённым экспериментам.
- `class_mapping.json` — соответствие индексов и названий классов.
- `sample_images/punching_hole_sample.jpg` — пример изображения для тестового запуска.

Ссылки для этапа 5:

- experiments notebook: `https://colab.research.google.com/drive/1a4tDSBWOxqjq7eHOj-rOM2J_oqxhKdP2?usp=sharing`
- final notebook: `https://colab.research.google.com/drive/1M7UG4lIfyHO01GoqDUuKJuW8FRvs0Gkt?usp=sharing`

Логика:

- экспериментальный ноутбук нужен для показа хода экспериментов, графиков и результатов;
- финальный ноутбук использует модель `resnet18`;
- все вспомогательные файлы лежат рядом, чтобы ноутбуки можно было запускать без поиска внешних артефактов.
