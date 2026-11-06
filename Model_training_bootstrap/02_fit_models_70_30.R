# 02_fit_models_70_30.R
#
# Step 2 of the workflow: fit the nine model x data combinations for 2005 and 2015 on a 70 % /
# 30 % split and write the plot-level predictions that Figure 2 (validation part) and
# Figure S1 (training part) are drawn from.
#
# Procedure:
#   set.seed(11); repeat i = 1..N { idx <- caret::createDataPartition(AGB, p = 0.7)
#                                   fit the model on the 70 % part, predict the 30 % part }
#   and write the actual/prediction pairs of the LAST repeat. data/matching_splits.csv lists,
#   per combination, the predictor table and the repeat N behind the Figure 2 file (validation)
#   and the Figure S1 file (training); this script replays exactly those sequences and writes
#     output/validation/<model>/<combination>/<year>.csv   (actual, prediction; 30 % part)
#     output/training/<model>/<combination>/<year>.csv     (actual, prediction; 70 % part)
#     output/fit_summary.csv                               (N, R2, RMSE, Bias per file)
#   and, when the sibling figure packages are present, compares the files with them.
#
# Model calls:
#   RF     randomForest(x = train[,-1], y = train$AGB, importance = TRUE)   # defaults otherwise
#   MLR    stepAIC(lm(AGB ~ ., train), direction = "backward")
#   Cubist cubist(x = train[,-1], y = train$AGB, committees = 10)
# Plots with AGB <= 0 or >= 200 Mg ha-1 are excluded first (164 plots remain in 2005, 930 in 2015).
# Metrics as in the Figure 2 script: R2 = squared correlation, RMSE, Bias = mean(actual - prediction).
#
# Usage (from the package root):  Rscript 02_fit_models_70_30.R [splits.csv] [output folder]
#   default splits.csv = data/matching_splits.csv, default output folder = output

suppressPackageStartupMessages({
  library(randomForest); library(caret); library(Cubist); library(MASS)
})
args <- commandArgs(trailingOnly = TRUE)
splits_csv <- if (length(args) >= 1) args[1] else "data/matching_splits.csv"
out_dir    <- if (length(args) >= 2) args[2] else "output"
splits <- read.csv(splits_csv, stringsAsFactors = FALSE)

table_dir <- "data/predictor_tables"
fig2_dir  <- "../Figure2_model_performance/data/prediction"
figS1_dir <- "../FigureS1_training_performance/data/training"
same <- function(a, b) length(a) == length(b) && isTRUE(all.equal(as.numeric(a), as.numeric(b), tolerance = 1e-6))

fit_predict <- function(model, train_df, test_df) {
  if (model == "RF") {
    fit <- randomForest(x = train_df[, -1], y = train_df$AGB, importance = TRUE)
    list(train = as.numeric(predict(fit, newdata = train_df)), test = as.numeric(predict(fit, newdata = test_df)))
  } else if (model == "MLR") {
    fit <- stepAIC(lm(AGB ~ ., data = train_df), direction = "backward", trace = 0)
    list(train = as.numeric(predict(fit, train_df[, -1])), test = as.numeric(predict(fit, test_df[, -1])))
  } else {
    fit <- cubist(x = train_df[, -1], y = train_df$AGB, committees = 10)
    list(train = as.numeric(predict(fit, newdata = train_df[, -1])), test = as.numeric(predict(fit, newdata = test_df[, -1])))
  }
}
metrics <- function(actual, pred) c(N = length(actual), R2 = cor(actual, pred)^2,
                                    RMSE = sqrt(mean((actual - pred)^2)), Bias = mean(actual - pred))

# replay the seed-11 sequence on one table up to `n_rep` and return that repeat's data and predictions
replay <- function(model, table_rel, n_rep) {
  df <- subset(read.csv(file.path(table_dir, table_rel)), AGB > 0 & AGB < 200)
  set.seed(11)
  for (i in seq_len(n_rep)) {
    idx <- createDataPartition(y = df$AGB, p = 0.7, list = FALSE)
    train_df <- df[idx, ]; test_df <- df[-idx, ]
    p <- fit_predict(model, train_df, test_df)
  }
  list(train = train_df, test = test_df, pred = p, n_plots = nrow(df))
}
write_pairs <- function(actual, pred, path) {
  dir.create(dirname(path), showWarnings = FALSE, recursive = TRUE)
  write.csv(data.frame(actual = actual, prediction = pred), path)   # same layout as the figure packages
}
compare_with <- function(ref_path, actual, pred) {
  if (!file.exists(ref_path)) return(NA)
  rf <- read.csv(ref_path); same(actual, rf$actual) && same(pred, rf$prediction)
}

rows <- list()
for (r in seq_len(nrow(splits))) {
  s <- splits[r, ]
  own <- file.path(s$Model, s$DataCombination, paste0(s$Year, ".csv"))
  pick <- function(x) if (is.null(x) || is.na(x) || !nzchar(x)) own else x   # empty cell = the combination's own table
  val_tab <- pick(s$validation_table)
  tr_tab  <- pick(s$training_table)
  cat(sprintf("%-7s %-15s %s: validation = %s repeat %d; training = %s repeat %d\n",
              s$Model, s$DataCombination, s$Year, val_tab, s$validation_repeat, tr_tab, s$training_repeat))

  v <- replay(s$Model, val_tab, s$validation_repeat)
  out <- file.path(out_dir, "validation", own)
  write_pairs(v$test$AGB, v$pred$test, out)
  rows[[length(rows) + 1]] <- data.frame(s[, c("Model", "DataCombination", "Year")], part = "validation",
    predictor_table = val_tab, repeat_no = s$validation_repeat, t(metrics(v$test$AGB, v$pred$test)),
    identical_to_figure_package = compare_with(file.path(fig2_dir, own), v$test$AGB, v$pred$test))

  t <- if (identical(tr_tab, val_tab) && s$training_repeat == s$validation_repeat) v else replay(s$Model, tr_tab, s$training_repeat)
  out <- file.path(out_dir, "training", own)
  write_pairs(t$train$AGB, t$pred$train, out)
  rows[[length(rows) + 1]] <- data.frame(s[, c("Model", "DataCombination", "Year")], part = "training",
    predictor_table = tr_tab, repeat_no = s$training_repeat, t(metrics(t$train$AGB, t$pred$train)),
    identical_to_figure_package = compare_with(file.path(figS1_dir, own), t$train$AGB, t$pred$train))
}
summary_df <- do.call(rbind, rows)
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
write.csv(summary_df, file.path(out_dir, "fit_summary.csv"), row.names = FALSE)
cat("\n"); print(summary_df, row.names = FALSE)
cat(sprintf("\n%d of %d files identical to the figure packages\n",
            sum(summary_df$identical_to_figure_package, na.rm = TRUE), nrow(summary_df)))
