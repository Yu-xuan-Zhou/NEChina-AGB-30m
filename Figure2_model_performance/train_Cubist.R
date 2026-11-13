# Figure 2 - Cubist fits
# ---------------------------------------------------------------------------------------------
# Fits the Cubist model for the three data combinations (Landsat+PALSAR, Landsat, PALSAR) and the
# two years (2005, 2015) and writes the validation data drawn in panels (d)-(f) of Figure 2.
#
# For each combination and year:
#   1. read data/training_input/Cubist/<combination>/<year>.csv (AGB in Mg ha-1 followed by the
#      predictors) and sort the plots by AGB;
#   2. set.seed(11), split the plots 70 % / 30 % (caret::createDataPartition),
#      fit a Cubist model with 10 committees on the 70 % part and predict the 30 % part;
#   3. write the observed and predicted AGB of the 30 % part to
#      data/prediction/Cubist/<combination>/<year>.csv and print N, R2, RMSE and Bias.
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
  AGB <- read.csv(file.path("data", "training_input", model_name, combination, paste0(year, ".csv")))
  AGB <- AGB[order(AGB$AGB), ]

  set.seed(11)
  trains   <- createDataPartition(y = AGB$AGB, p = 0.7, list = FALSE)
  training <- AGB[trains, ]
  testing  <- AGB[-trains, ]
  model    <- fit_model(training)
  testpred <- predict_model(model, testing)

  # validation data: observed and predicted AGB (Mg ha-1)
  out <- file.path("data", "prediction", model_name, combination, paste0(year, ".csv"))
  dir.create(dirname(out), showWarnings = FALSE, recursive = TRUE)
  write.csv(data.frame(actual = testing$AGB, prediction = testpred), out)

  cat(sprintf("%-6s %-15s %d  N = %3d  R2 = %.2f  RMSE = %.2f  Bias = %.2f\n",
              model_name, combination, year, nrow(testing),
              1 - sum((testing$AGB - testpred)^2) / sum((testing$AGB - mean(testing$AGB))^2),
              sqrt(mean((testing$AGB - testpred)^2)),
              mean(testpred - testing$AGB)))
}
