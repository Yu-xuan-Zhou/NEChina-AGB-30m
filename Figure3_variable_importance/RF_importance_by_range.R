# Figure 3 - random forest variable importance by AGB range
# ---------------------------------------------------------------------------------------------
# For each year (2005, 2015) and AGB range (0-200, 0-50, 50-100, 100-150, 150-200 Mg ha-1):
#   1. read data/training_input/Landsat+Palsar_<year>.csv (AGB in Mg ha-1 followed by the
#      Landsat + PALSAR predictors of the RF model) and keep the plots inside the range;
#   2. set.seed(11), then repeat 100 times: split the plots 70 % / 30 % (caret::createDataPartition)
#      and fit a random forest on the 70 % part (importance = TRUE);
#   3. take the variable importance of the last model (caret::varImp, i.e. the permutation
#      importance %IncMSE), drop the predictors with a non-positive value and express the rest
#      as shares (%) of their sum;
#   4. write output/importance_by_range/RF_<year>_<low>_<high>.csv (columns: index, important, Range).
#
# Run from this folder:  Rscript RF_importance_by_range.R
# Packages: randomForest, caret

suppressPackageStartupMessages({
  library(randomForest)
  library(caret)
})

years   <- c(2005, 2015)
ranges  <- list(c(0, 200), c(0, 50), c(50, 100), c(100, 150), c(150, 200))
repeats <- 100
out_dir <- file.path("output", "importance_by_range")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

for (year in years) {
  plots <- read.csv(file.path("data", "training_input", paste0("Landsat+Palsar_", year, ".csv")))

  for (rg in ranges) {
    # plots of this AGB range; AGB is the first column, the predictors follow
    AGB <- subset(plots, AGB > rg[1] & AGB < rg[2])
    form_reg <- as.formula(paste0("AGB~", paste(colnames(AGB)[-1], collapse = "+")))

    set.seed(11)
    for (i in seq_len(repeats)) {
      trains     <- createDataPartition(y = AGB$AGB, p = 0.7, list = FALSE)
      traindata  <- AGB[trains, ]
      fit_rf_reg <- randomForest(form_reg, data = traindata, importance = TRUE)
    }

    # importance of the last model, positive values only, as shares in percent
    imp <- varImp(fit_rf_reg)
    a <- imp$Overall
    names(a) <- rownames(imp)
    a <- a[a > 0]
    percentages <- a / sum(a) * 100

    df <- data.frame(index = names(percentages), important = as.numeric(percentages),
                     Range = paste0(rg[1], "-", rg[2]))
    df <- df[order(-df$important), ]
    out <- file.path(out_dir, sprintf("RF_%d_%d_%d.csv", year, rg[1], rg[2]))
    write.csv(df, out, row.names = FALSE)
    cat(sprintf("%d  %3d-%-3d  %3d plots  %2d predictors with positive importance; first: %s %.1f %%\n",
                year, rg[1], rg[2], nrow(AGB), nrow(df), df$index[1], df$important[1]))
  }
}
