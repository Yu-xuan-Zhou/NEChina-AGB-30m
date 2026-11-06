# Table 1 - Bootstrap accuracy of the nine model x data combinations
# ----------------------------------------------------------------
# 100 bootstrap repeats per model (RF, MLR, Cubist) x data combination
# (Landsat+Palsar, Landsat, Palsar) x year (2005, 2015); 80 % / 20 % random split
# (set.seed(123)); R2, RMSE and Bias (mean of predictions - mean of observations)
# on the 20 % test part. Input: data/filtered_variables/<model>/<combination>/<year>.csv
# (AGB in Mg ha-1 plus the predictor columns selected for that model).
# Output: output/bootstrap_comparison_table.csv (manuscript Table 1) and three detail tables.
# Run from this folder: Rscript Table1_bootstrap_accuracy.R   (about 5 min)

#––– PACKAGES –––
library(randomForest)    # for RF
library(Cubist)          # for Cubist
library(caret)           # for data splitting & metrics
library(dplyr)           # for data manipulation
library(tidyr)           # for data reshaping

#––– SETTINGS –––
set.seed(123)            # reproducibility
n_iter    <- 100         # number of bootstrap repeats
split_prop <- 0.8        # 80% train / 20% test

#––– DEFINE ALL COMBINATIONS –––
models <- c("RF", "MLR", "Cubist")
data_combinations <- c("Landsat+Palsar", "Landsat", "Palsar")
years <- c("2005", "2015")

#––– STORAGE FOR ALL RESULTS –––
all_results <- data.frame()

#––– MAIN LOOP FOR ALL COMBINATIONS –––
for (model_type in models) {
  for (data_comb in data_combinations) {
    for (year in years) {
      
      # Construct file path
      file_path <- paste0("data/filtered_variables/",
                          model_type, "/", data_comb, "/", year, ".csv")
      
      # Check if file exists
      if (!file.exists(file_path)) {
        cat("File not found:", file_path, "\n")
        next
      }
      
      # Load data
      df <- read.csv(file_path, header = TRUE, stringsAsFactors = FALSE)
      cat("Processing:", model_type, "-", data_comb, "-", year, "\n")
      
      # Storage for this combination's results
      combo_results <- data.frame(
        Iter = 1:n_iter,
        Model = model_type,
        DataCombination = data_comb,
        Year = year,
        R2 = NA_real_,
        RMSE = NA_real_,
        Bias = NA_real_,
        Min = NA_real_,
        Max = NA_real_,
        Mean = NA_real_
      )
      
      # Bootstrap iterations
      for (i in seq_len(n_iter)) {
        # 1) Split into train/test
        train_idx <- createDataPartition(df$AGB, p = split_prop, list = FALSE)
        train_df  <- df[train_idx, ]
        test_df   <- df[-train_idx, ]
        
        # 2) Train and predict based on model type
        if (model_type == "RF") {
          # Random Forest
          mod <- randomForest(AGB ~ ., data = train_df, importance = TRUE)
          pred <- predict(mod, newdata = test_df)
          
        } else if (model_type == "Cubist") {
          # Cubist
          predictors <- train_df %>% select(-AGB)
          response <- train_df$AGB
          mod <- cubist(predictors, response)
          pred <- predict(mod, newdata = test_df %>% select(-AGB))
          
        } else if (model_type == "MLR") {
          # Multiple Linear Regression
          mod <- lm(AGB ~ ., data = train_df)
          pred <- predict(mod, newdata = test_df)
        }
        
        # 3) Calculate metrics
        # R-squared
        ss_tot <- sum((test_df$AGB - mean(test_df$AGB))^2)
        ss_res <- sum((test_df$AGB - pred)^2)
        r2_val <- 1 - (ss_res / ss_tot)
        
        # RMSE
        rmse_val <- sqrt(mean((pred - test_df$AGB)^2))
        
        # Bias (mean of predictions - mean of observations)
        bias_val <- mean(pred) - mean(test_df$AGB)
        
        # Min, Max, Mean of predictions
        min_val <- min(pred)
        max_val <- max(pred)
        mean_val <- mean(pred)
        
        # 4) Store results
        combo_results[i, c("R2", "RMSE", "Bias", "Min", "Max", "Mean")] <- 
          c(r2_val, rmse_val, bias_val, min_val, max_val, mean_val)
      }
      
      # Append to all results
      all_results <- rbind(all_results, combo_results)
    }
  }
}

#––– SUMMARIZE RESULTS –––
# Summary statistics for each model-data-year combination
summary_stats <- all_results %>%
  group_by(Model, DataCombination, Year) %>%
  summarize(
    # Mean and SD of R2
    mean_R2 = mean(R2, na.rm = TRUE),
    sd_R2 = sd(R2, na.rm = TRUE),
    
    # Mean and SD of RMSE
    mean_RMSE = mean(RMSE, na.rm = TRUE),
    sd_RMSE = sd(RMSE, na.rm = TRUE),
    
    # Mean and SD of Bias
    mean_Bias = mean(Bias, na.rm = TRUE),
    sd_Bias = sd(Bias, na.rm = TRUE),
    
    # Overall Min and Max across all iterations
    overall_Min = min(Min, na.rm = TRUE),
    overall_Max = max(Max, na.rm = TRUE),
    
    # Mean of the means
    mean_Mean = mean(Mean, na.rm = TRUE),
    
    # Percentiles for R2 and RMSE
    R2_25th = quantile(R2, 0.25, na.rm = TRUE),
    R2_50th = quantile(R2, 0.50, na.rm = TRUE),
    R2_75th = quantile(R2, 0.75, na.rm = TRUE),
    RMSE_25th = quantile(RMSE, 0.25, na.rm = TRUE),
    RMSE_50th = quantile(RMSE, 0.50, na.rm = TRUE),
    RMSE_75th = quantile(RMSE, 0.75, na.rm = TRUE),
    
    .groups = 'drop'
  )

# Print summary
print("Summary Statistics (units: Mg ha-1)")
print(summary_stats)

#––– DETAILED OUTPUT –––
# Create a more detailed summary table
detailed_summary <- all_results %>%
  group_by(Model, DataCombination, Year) %>%
  summarize(
    n_iterations = sum(!is.na(RMSE)),
    R2_mean = round(mean(R2, na.rm = TRUE), 2),
    R2_sd = round(sd(R2, na.rm = TRUE), 2),
    RMSE_mean = round(mean(RMSE, na.rm = TRUE), 2),
    RMSE_sd = round(sd(RMSE, na.rm = TRUE), 2),
    Bias_mean = round(mean(Bias, na.rm = TRUE), 2),
    Bias_sd = round(sd(Bias, na.rm = TRUE), 2),
    Min_range = paste0("[", round(min(Min, na.rm = TRUE), 2), ", ", 
                       round(max(Min, na.rm = TRUE), 2), "]"),
    Max_range = paste0("[", round(min(Max, na.rm = TRUE), 2), ", ", 
                       round(max(Max, na.rm = TRUE), 2), "]"),
    Mean_avg = round(mean(Mean, na.rm = TRUE), 2),
    .groups = 'drop'
  )

print("\nDetailed Summary Table:")
print(detailed_summary)

#––– SAVE RESULTS –––
# Save all iteration results
write.csv(all_results, "output/all_bootstrap_results.csv", row.names = FALSE)

# Save summary statistics
write.csv(summary_stats, "output/bootstrap_summary_stats.csv", row.names = FALSE)

# Save detailed summary
write.csv(detailed_summary, "output/bootstrap_detailed_summary.csv", row.names = FALSE)

#––– VISUALIZATION (Optional) –––
# Plot RMSE distributions
library(ggplot2)

# R-squared boxplot
p0 <- ggplot(all_results, aes(x = Model, y = R2, fill = DataCombination)) +
  geom_boxplot() +
  facet_wrap(~ Year) +
  labs(title = "R² Distribution by Model, Data Combination, and Year",
       y = "R²",
       x = "Model") +
  theme_minimal() +
  ylim(0, 1)

ggsave("output/r2_distribution.png", p0, width = 10, height = 6, dpi = 300)

# RMSE boxplot
p1 <- ggplot(all_results, aes(x = Model, y = RMSE, fill = DataCombination)) +
  geom_boxplot() +
  facet_wrap(~ Year) +
  labs(title = "RMSE Distribution by Model, Data Combination, and Year",
       y = expression("RMSE (Mg ha"^-1*")"),
       x = "Model") +
  theme_minimal()

ggsave("output/rmse_distribution.png", p1, width = 10, height = 6, dpi = 300)

# Bias boxplot
p2 <- ggplot(all_results, aes(x = Model, y = Bias, fill = DataCombination)) +
  geom_boxplot() +
  facet_wrap(~ Year) +
  labs(title = "Bias Distribution by Model, Data Combination, and Year",
       y = expression("Bias (Mg ha"^-1*")"),
       x = "Model") +
  theme_minimal() +
  geom_hline(yintercept = 0, linetype = "dashed", color = "red")

ggsave("output/bias_distribution.png", p2, width = 10, height = 6, dpi = 300)

#––– CREATE COMPARISON TABLE –––
# Create a formatted comparison table
comparison_table <- all_results %>%
  group_by(Model, DataCombination, Year) %>%
  summarize(
    R2 = paste0(round(mean(R2, na.rm = TRUE), 2), " ± ", 
                round(sd(R2, na.rm = TRUE), 2)),
    RMSE = paste0(round(mean(RMSE, na.rm = TRUE), 2), " ± ", 
                  round(sd(RMSE, na.rm = TRUE), 2)),
    Bias = paste0(round(mean(Bias, na.rm = TRUE), 2), " ± ", 
                  round(sd(Bias, na.rm = TRUE), 2)),
    Min = round(min(Min, na.rm = TRUE), 2),
    Max = round(max(Max, na.rm = TRUE), 2),
    Mean = round(mean(Mean, na.rm = TRUE), 2),
    .groups = 'drop'
  ) %>%
  arrange(Year, DataCombination, Model)

print("\nFormatted Comparison Table (Mean ± SD):")
print(comparison_table)

# Save formatted table
write.csv(comparison_table, "output/bootstrap_comparison_table.csv", row.names = FALSE)

#––– BEST MODEL IDENTIFICATION –––
# Find best model for each data combination and year (based on highest mean R2 and lowest mean RMSE)
best_models_r2 <- all_results %>%
  group_by(Model, DataCombination, Year) %>%
  summarize(
    mean_R2 = mean(R2, na.rm = TRUE),
    mean_RMSE = mean(RMSE, na.rm = TRUE),
    .groups = 'drop'
  ) %>%
  group_by(DataCombination, Year) %>%
  slice_max(mean_R2) %>%
  ungroup()

best_models_rmse <- all_results %>%
  group_by(Model, DataCombination, Year) %>%
  summarize(
    mean_R2 = mean(R2, na.rm = TRUE),
    mean_RMSE = mean(RMSE, na.rm = TRUE),
    .groups = 'drop'
  ) %>%
  group_by(DataCombination, Year) %>%
  slice_min(mean_RMSE) %>%
  ungroup()

print("\nBest Models (highest R²) for each combination:")
print(best_models_r2)

print("\nBest Models (lowest RMSE) for each combination:")
print(best_models_rmse)

cat("\nAnalysis complete! Results saved to CSV files.\n")