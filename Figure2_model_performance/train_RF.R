# Figure 2 - random forest (RF) fits
# ---------------------------------------------------------------------------------------------
# Fits the RF model for the three data combinations (Landsat+PALSAR, Landsat, PALSAR) and the two
# years (2005, 2015) and writes the validation data drawn in panels (a)-(c) of Figure 2.
#
# For each combination and year:
#   1. read data/training_input/RF/<combination>/<year>.csv (AGB in Mg ha-1 followed by the
#      predictors) and sort the plots by AGB;
#   2. set.seed(11), split the plots 70 % / 30 % (caret::createDataPartition),
#      fit the model on the 70 % part and predict the 30 % part;
#   3. write the observed and predicted AGB of the 30 % part to
#      data/prediction/RF/<combination>/<year>.csv and print N, R2, RMSE and Bias.
#
# Run from this folder:  Rscript train_RF.R
# Packages: randomForest, caret

suppressPackageStartupMessages({
  library(randomForest)
  library(caret)
})

model_name <- "RF"
runs <- data.frame(
  combination = c("Landsat+Palsar", "Landsat", "Palsar", "Landsat+Palsar", "Landsat", "Palsar"),
  year        = c(2005, 2005, 2005, 2015, 2015, 2015),
  stringsAsFactors = FALSE
)

# randomForest defaults: 500 trees, mtry = floor(number of predictors / 3)
fit_model <- function(training) {
  randomForest(x = training[, -1], y = training$AGB,
               ntree = 500, mtry = max(floor((ncol(training) - 1) / 3), 1), importance = TRUE)
}
predict_model <- function(model, testing) {
  as.numeric(predict(model, newdata = testing))
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
