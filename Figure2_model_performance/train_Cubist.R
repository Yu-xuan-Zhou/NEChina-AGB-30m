# Figure 2 - Cubist fits
# ---------------------------------------------------------------------------------------------
# Fits the Cubist model for the three data combinations (Landsat+PALSAR, Landsat, PALSAR) and the
# two years (2005, 2015) and writes the validation data drawn in panels (d)-(f) of Figure 2.
#
# For each combination and year:
#   1. read the predictor table data/training_input/<table>/<combination>/<year>.csv (AGB in
#      Mg ha-1 followed by the predictors; <table> is listed in `runs` below) and keep the plots
#      with 0 < AGB < 200 Mg ha-1;
#   2. set.seed(11), then repeat N times: split the plots 70 % / 30 % (caret::createDataPartition),
#      fit a Cubist model with 10 committees on the 70 % part and predict the 30 % part;
#   3. write the observed and predicted AGB of the last repeat to
#      data/prediction/Cubist/<combination>/<year>.csv and print N, R2, RMSE and Bias.
# N, the number of repeats of the run that is plotted, is listed in `runs` below.
#
# Run from this folder:  Rscript train_Cubist.R
# Packages: Cubist, caret

suppressPackageStartupMessages({
  library(Cubist)
  library(caret)
})

model_name <- "Cubist"
runs <- data.frame(
  combination = c("Landsat+Palsar", "Landsat", "Palsar", "Landsat+Palsar", "Landsat", "Palsar"),
  year        = c(2005, 2005, 2005, 2015, 2015, 2015),
  table       = c("RF", "RF", "RF", "Cubist", "Cubist", "Cubist"),
  repeats     = c(23, 23, 23, 14, 14, 14),
  stringsAsFactors = FALSE
)

# rule-based model trees, 10 committees
fit_model <- function(training) {
  cubist(x = training[, -1], y = training$AGB, committees = 10)
}
predict_model <- function(model, testing) {
  as.numeric(predict(model, newdata = testing[, -1]))
}

for (r in seq_len(nrow(runs))) {
  combination <- runs$combination[r]
  year <- runs$year[r]

  # AGB is the first column, the predictors follow
  AGB <- read.csv(file.path("data", "training_input", runs$table[r], combination, paste0(year, ".csv")))
  AGB <- subset(AGB, AGB > 0 & AGB < 200)

  set.seed(11)
  for (i in seq_len(runs$repeats[r])) {
    trains   <- createDataPartition(y = AGB$AGB, p = 0.7, list = FALSE)
    training <- AGB[trains, ]
    testing  <- AGB[-trains, ]
    model    <- fit_model(training)
    testpred <- predict_model(model, testing)
  }

  # validation data of the last repeat: observed and predicted AGB (Mg ha-1)
  out <- file.path("data", "prediction", model_name, combination, paste0(year, ".csv"))
  dir.create(dirname(out), showWarnings = FALSE, recursive = TRUE)
  write.csv(data.frame(actual = testing$AGB, prediction = testpred), out)

  cat(sprintf("%-6s %-15s %d  repeat %3d  N = %3d  R2 = %.2f  RMSE = %.2f  Bias = %.2f\n",
              model_name, combination, year, runs$repeats[r], nrow(testing),
              cor(testing$AGB, testpred)^2,
              sqrt(mean((testing$AGB - testpred)^2)),
              mean(testing$AGB - testpred)))
}
