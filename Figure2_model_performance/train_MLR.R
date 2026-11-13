# Figure 2 - multiple linear regression (MLR) fits
# ---------------------------------------------------------------------------------------------
# Fits the MLR model for the three data combinations (Landsat+PALSAR, Landsat, PALSAR) and the
# two years (2005, 2015) and writes the validation data drawn in panels (g)-(i) of Figure 2.
#
# For each combination and year:
#   1. read data/training_input/MLR/<combination>/<year>.csv (AGB in Mg ha-1 followed by the
#      predictors) and sort the plots by AGB;
#   2. set.seed(11), split the plots 70 % / 30 % (caret::createDataPartition),
#      fit a linear model on the 70 % part, reduce it by backward stepwise selection
#      (MASS::stepAIC) and predict the 30 % part;
#   3. write the observed and predicted AGB of the 30 % part to
#      data/prediction/MLR/<combination>/<year>.csv and print N, R2, RMSE and Bias.
#
# Run from this folder:  Rscript train_MLR.R
# Packages: MASS, caret

suppressPackageStartupMessages({
  library(MASS)
  library(caret)
})

model_name <- "MLR"
runs <- data.frame(
  combination = c("Landsat+Palsar", "Landsat", "Palsar", "Landsat+Palsar", "Landsat", "Palsar"),
  year        = c(2005, 2005, 2005, 2015, 2015, 2015),
  stringsAsFactors = FALSE
)

# linear model with all predictors, then backward stepwise selection by AIC
fit_model <- function(training) {
  line.model <- lm(AGB ~ ., data = training)
  stepAIC(line.model, direction = "backward", trace = 0)
}
predict_model <- function(model, testing) {
  as.numeric(predict(model, testing[, -1]))
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
