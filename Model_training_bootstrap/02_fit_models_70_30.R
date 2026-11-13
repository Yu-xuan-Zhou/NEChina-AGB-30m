# 02_fit_models_70_30.R
#
# Step 2 of the workflow: fit the nine model x data combinations for 2005 and 2015 on a 70 % /
# 30 % split and write the plot-level predictions that Figure 2 (validation part) and
# Figure S1 (training part) are drawn from.
#
# Procedure:
#   sort the plots by AGB; set.seed(11); idx <- caret::createDataPartition(AGB, p = 0.7);
#   fit the model on the 70 % part, predict both parts and write
#     output/validation/<model>/<combination>/<year>.csv   (actual, prediction; 30 % part)
#     output/training/<model>/<combination>/<year>.csv     (actual, prediction; 70 % part)
#     output/fit_summary.csv                               (N, R2, RMSE, Bias per file)
#   and, when the sibling figure packages are present, compares the files with them.
#
# Model calls:
#   RF     randomForest(x = train[,-1], y = train$AGB, ntree = 500, mtry = floor(p / 3), importance = TRUE)
#   MLR    stepAIC(lm(AGB ~ ., train), direction = "backward")
#   Cubist cubist(x = train[,-1], y = train$AGB, committees = 10)
# Metrics as in the Figure 2 script: R2 = 1 - SSres / SStot, RMSE, Bias = mean(prediction - actual).
#
# Usage (from the package root):  Rscript 02_fit_models_70_30.R [output folder]
#   default output folder = output

suppressPackageStartupMessages({
  library(randomForest); library(caret); library(Cubist); library(MASS)
})
args <- commandArgs(trailingOnly = TRUE)
out_dir <- if (length(args) >= 1) args[1] else "output"

table_dir <- "data/predictor_tables"
fig2_dir  <- "../Figure2_model_performance/data/prediction"
figS1_dir <- "../FigureS1_training_performance/data/training"
same <- function(a, b) length(a) == length(b) && isTRUE(all.equal(as.numeric(a), as.numeric(b), tolerance = 1e-6))

fit_predict <- function(model, train_df, test_df) {
  if (model == "RF") {
    fit <- randomForest(x = train_df[, -1], y = train_df$AGB,
                        ntree = 500, mtry = max(floor((ncol(train_df) - 1) / 3), 1), importance = TRUE)
    list(train = as.numeric(predict(fit, newdata = train_df)), test = as.numeric(predict(fit, newdata = test_df)))
  } else if (model == "MLR") {
    fit <- stepAIC(lm(AGB ~ ., data = train_df), direction = "backward", trace = 0)
    list(train = as.numeric(predict(fit, train_df[, -1])), test = as.numeric(predict(fit, test_df[, -1])))
  } else {
    fit <- cubist(x = train_df[, -1], y = train_df$AGB, committees = 10)
    list(train = as.numeric(predict(fit, newdata = train_df[, -1])), test = as.numeric(predict(fit, newdata = test_df[, -1])))
  }
}
metrics <- function(actual, pred) c(N = length(actual), R2 = 1 - sum((actual - pred)^2) / sum((actual - mean(actual))^2),
                                    RMSE = sqrt(mean((actual - pred)^2)), Bias = mean(pred - actual))

write_pairs <- function(actual, pred, path) {
  dir.create(dirname(path), showWarnings = FALSE, recursive = TRUE)
  write.csv(data.frame(actual = actual, prediction = pred), path)   # same layout as the figure packages
}
compare_with <- function(ref_path, actual, pred) {
  if (!file.exists(ref_path)) return(NA)
  rf <- read.csv(ref_path); same(actual, rf$actual) && same(pred, rf$prediction)
}

rows <- list()
for (model in c("RF", "MLR", "Cubist")) for (combination in c("Landsat+Palsar", "Landsat", "Palsar")) for (year in c(2005, 2015)) {
  own <- file.path(model, combination, paste0(year, ".csv"))
  df <- read.csv(file.path(table_dir, own))
  df <- df[order(df$AGB), ]

  set.seed(11)
  idx <- createDataPartition(y = df$AGB, p = 0.7, list = FALSE)
  train_df <- df[idx, ]; test_df <- df[-idx, ]
  p <- fit_predict(model, train_df, test_df)

  write_pairs(test_df$AGB, p$test, file.path(out_dir, "validation", own))
  rows[[length(rows) + 1]] <- data.frame(Model = model, DataCombination = combination, Year = year, part = "validation",
    t(metrics(test_df$AGB, p$test)),
    identical_to_figure_package = compare_with(file.path(fig2_dir, own), test_df$AGB, p$test))

  write_pairs(train_df$AGB, p$train, file.path(out_dir, "training", own))
  rows[[length(rows) + 1]] <- data.frame(Model = model, DataCombination = combination, Year = year, part = "training",
    t(metrics(train_df$AGB, p$train)),
    identical_to_figure_package = compare_with(file.path(figS1_dir, own), train_df$AGB, p$train))
}
summary_df <- do.call(rbind, rows)
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
write.csv(summary_df, file.path(out_dir, "fit_summary.csv"), row.names = FALSE)
cat("\n"); print(summary_df, row.names = FALSE)
cat(sprintf("\n%d of %d files identical to the figure packages\n",
            sum(summary_df$identical_to_figure_package, na.rm = TRUE), nrow(summary_df)))
