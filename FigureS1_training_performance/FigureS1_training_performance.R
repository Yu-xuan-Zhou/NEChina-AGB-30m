# Figure S1 - Model performance on the training data (9 panels)
# ---------------------------------------------------------------
# Rows: RF, Cubist, MLR; columns: Landsat+PALSAR, Landsat, PALSAR.
# Each panel plots field AGB density (x) against predicted AGB density (y)
# for 2005 (red) and 2015 (grey), with N, R2, RMSE and Bias per year.
#
# Input : data/training/<model>/<data combination>/{2005,2015}.csv
#         (columns: actual, prediction; units Mg ha-1)
# Output: output/FigureS1_training_performance.jpg
#
# Run from this folder, e.g.  Rscript FigureS1_training_performance.R
# Identical to Figure2_model_performance.R except for the input folder and output name.
# Requires: ggplot2, ggpubr, gridExtra, grid

library(ggpubr)
library(gridExtra)
library(grid)

# Panel (a): with legend
generate_plot1 <- function(folder_path, title="RF_Landsat+Palsar", annotation_size=3) {
  # Colours for the two years
  color_2015 <- "#939393"
    color_2005 <- "red"

    # Read data from the specified folder
    df1 <- read.csv(file.path(folder_path, "2005.csv"))
    num_2005 <- nrow(df1)
    df1$Year <- "2005"

    df2 <- read.csv(file.path(folder_path, "2015.csv"))
    df2$Year <- "2015"
    num_2015 <- nrow(df2)

    # RMSE and Bias (observed - predicted) for 2005
    rmse_2005 <- sqrt(mean((df1$actual - df1$prediction)^2))
    bias_2005 <- mean(df1$actual - df1$prediction)

    # RMSE and Bias for 2015
    rmse_2015 <- sqrt(mean((df2$actual - df2$prediction)^2))
    bias_2015 <- mean(df2$actual - df2$prediction)

    # Theme sized for high-resolution output (scaled down at export)
    custom_theme <- theme(
      text = element_text(family = 'Arial', size = 24),
      plot.title = element_text(hjust = 0, face = 'bold', size = 24),
      axis.title = element_text(size = 24),
      axis.text = element_text(size = 24),
      axis.line = element_line(size = 1, colour="black"),
      legend.position = c(0.75, 0.225),
      legend.justification = c(0, 0),
      legend.text = element_text(size = 20),
      legend.title = element_text(size = 20),
      legend.key.size = unit(0.6, "lines"),
      panel.background = element_blank(),
      panel.grid.major = element_blank(),
      panel.grid.minor = element_blank(),

    )

    plot.theme <- theme_minimal()

    # Annotation text size
    annotation_size_scaled <- annotation_size * 2

    plot <- ggplot(rbind(df2, df1), aes(x = actual, y = prediction)) +
      geom_point(aes(color = Year, shape = Year), size = 2.5, stroke = 0) +
      scale_color_manual(values = c("2015" = color_2015, "2005" = color_2005), name = "Year") +
      scale_shape_manual(values = c("2005" = 16, "2015" = 16)) +
      xlab(expression("Field AGB Density (Mg ha"^-1*")")) +
      ylab(expression("Predicted AGB Density (Mg ha"^-1*")")) +
      xlim(1, 200) +
      ylim(1, 200) +
      ggtitle(title) +
      stat_regline_equation(data = subset(rbind(df1, df2), Year == "2005"),
                            aes(label = ..rr.label.., color = Year),
                            label.x = 10, label.y = 186,
                            size = annotation_size_scaled, show.legend = FALSE) +
      annotate("text", x = 10, y = 198, label = paste("N = ", num_2005),
               hjust = 0, color = color_2005, size = annotation_size_scaled) +
      annotate("text", x = 10, y = 172, label = paste("RMSE = ", round(rmse_2005, 2)),
               hjust = 0, color = color_2005, size = annotation_size_scaled) +
      annotate("text", x = 10, y = 160, label = paste("Bias = ", round(bias_2005, 2)),
               hjust = 0, color = color_2005, size = annotation_size_scaled) +
      stat_regline_equation(data = subset(rbind(df1, df2), Year == "2015"),
                            aes(label = ..rr.label.., color = Year),
                            label.x = 110, label.y = 36,
                            size = annotation_size_scaled, show.legend = FALSE) +
      annotate("text", x = 110, y = 48, label = paste("N = ", num_2015),
               hjust = 0, color = color_2015, size = annotation_size_scaled) +
      annotate("text", x = 110, y = 22, label = paste("RMSE = ", round(rmse_2015, 2)),
               hjust = 0, color = color_2015, size = annotation_size_scaled) +
      annotate("text", x = 110, y = 10, label = paste("Bias = ", round(bias_2015, 2)),
               hjust = 0, color = color_2015, size = annotation_size_scaled) +
      annotate("segment", x = 1, xend = 200, y = 1, yend = 200,
               color = "black", linetype = "solid", size = 0.5) +   # 1:1 line
      scale_color_manual(values = c("2005" = color_2005, "2015" = color_2015), name = "Year") +
      theme_bw() +
      plot.theme +
      custom_theme

    return(plot)
}

# Panels (b)-(i): same as above, without legend
generate_plot2 <- function(folder_path, title="RF_Landsat+Palsar", annotation_size=3) {
  # Colours for the two years
  color_2015 <- "#939393"
    color_2005 <- "red"

    # Read data from the specified folder
    df1 <- read.csv(file.path(folder_path, "2005.csv"))
    num_2005 <- nrow(df1)
    df1$Year <- "2005"

    df2 <- read.csv(file.path(folder_path, "2015.csv"))
    num_2015 <- nrow(df2)
    df2$Year <- "2015"

    # RMSE and Bias (observed - predicted) for 2005
    rmse_2005 <- sqrt(mean((df1$actual - df1$prediction)^2))
    bias_2005 <- mean(df1$actual - df1$prediction)

    # RMSE and Bias for 2015
    rmse_2015 <- sqrt(mean((df2$actual - df2$prediction)^2))
    bias_2015 <- mean(df2$actual - df2$prediction)

    # Theme sized for high-resolution output (scaled down at export)
    custom_theme <- theme(
      text = element_text(family = "Arial", size = 24),
      axis.title = element_text(size = 24),
      axis.text = element_text(size = 24),
      axis.line = element_line(size = 1, colour="black"),
      plot.title = element_text(hjust = 0, face = 'bold', size = 24),
      legend.position = "none",
      panel.grid.major = element_blank(),
      panel.grid.minor = element_blank(),
      panel.background = element_blank()
    )

    plot.theme <- theme_minimal()

    # Annotation text size
    annotation_size_scaled <- annotation_size * 2

    plot <- ggplot(rbind(df2, df1), aes(x = actual, y = prediction)) +
      geom_point(aes(color = Year, shape = Year), size = 2.5, stroke = 0) +
      scale_color_manual(values = c("2015" = color_2015, "2005" = color_2005), name = "Year") +
      scale_shape_manual(values = c("2005" = 16, "2015" = 16)) +
      xlab(expression("Field AGB Density (Mg ha"^-1*")")) +
      ylab(expression("Predicted AGB Density (Mg ha"^-1*")")) +
      xlim(1, 200) +
      ylim(1, 200) +
      ggtitle(title) +
      stat_regline_equation(data = subset(rbind(df1, df2), Year == "2005"),
                            aes(label = ..rr.label.., color = Year),
                            label.x = 10, label.y = 186,
                            size = annotation_size_scaled, show.legend = FALSE) +
      annotate("text", x = 10, y = 198, label = paste("N = ", num_2005),
               hjust = 0, color = color_2005, size = annotation_size_scaled) +
      annotate("text", x = 10, y = 172, label = paste("RMSE = ", round(rmse_2005, 2)),
               hjust = 0, color = color_2005, size = annotation_size_scaled) +
      annotate("text", x = 10, y = 160, label = paste("Bias = ", round(bias_2005, 2)),
               hjust = 0, color = color_2005, size = annotation_size_scaled) +
      stat_regline_equation(data = subset(rbind(df1, df2), Year == "2015"),
                            aes(label = ..rr.label.., color = Year),
                            label.x = 110, label.y = 36,
                            size = annotation_size_scaled, show.legend = FALSE) +
      annotate("text", x = 110, y = 48, label = paste("N = ", num_2015),
               hjust = 0, color = color_2015, size = annotation_size_scaled) +
      annotate("text", x = 110, y = 22, label = paste("RMSE = ", round(rmse_2015, 2)),
               hjust = 0, color = color_2015, size = annotation_size_scaled) +
      annotate("text", x = 110, y = 10, label = paste("Bias = ", round(bias_2015, 2)),
               hjust = 0, color = color_2015, size = annotation_size_scaled) +
      annotate("segment", x = 1, xend = 200, y = 1, yend = 200,
               color = "black", linetype = "solid", size = 0.5) +   # 1:1 line
      scale_color_manual(values = c("2005" = color_2005, "2015" = color_2015), name = "Year") +
      theme_bw() +
      plot.theme +
      custom_theme

    return(plot)
}

# Input folders (relative to this script's folder)
data_root <- "data/training"
folder_path1 <- file.path(data_root, "RF",     "Landsat+Palsar")
folder_path2 <- file.path(data_root, "RF",     "Landsat")
folder_path3 <- file.path(data_root, "RF",     "Palsar")
folder_path4 <- file.path(data_root, "Cubist", "Landsat+Palsar")
folder_path5 <- file.path(data_root, "Cubist", "Landsat")
folder_path6 <- file.path(data_root, "Cubist", "Palsar")
folder_path7 <- file.path(data_root, "MLR",    "Landsat+Palsar")
folder_path8 <- file.path(data_root, "MLR",    "Landsat")
folder_path9 <- file.path(data_root, "MLR",    "Palsar")

# Base annotation size
annotation_size = 4

# Build all panels
plot_1 <- generate_plot1(folder_path1, title="(a) RF_Landsat+Palsar", annotation_size)
plot_2 <- generate_plot2(folder_path2, title="(b) RF_Landsat", annotation_size)
plot_3 <- generate_plot2(folder_path3, title="(c) RF_Palsar", annotation_size)
plot_4 <- generate_plot2(folder_path4, title="(d) Cubist_Landsat+Palsar", annotation_size)
plot_5 <- generate_plot2(folder_path5, title="(e) Cubist_Landsat", annotation_size)
plot_6 <- generate_plot2(folder_path6, title="(f) Cubist_Palsar", annotation_size)
plot_7 <- generate_plot2(folder_path7, title="(g) MLR_Landsat+Palsar", annotation_size)
plot_8 <- generate_plot2(folder_path8, title="(h) MLR_Landsat", annotation_size)
plot_9 <- generate_plot2(folder_path9, title="(i) MLR_Palsar", annotation_size)

# Arrange 3 x 3. A scratch PNG device is opened first so that text metrics
# are computed with Arial even when running non-interactively (Rscript);
# otherwise R falls back to a PDF device where Arial is unavailable.
scratch_dev <- tempfile(fileext = ".png")
png(scratch_dev, width = 1200, height = 1200)
combined_plot <- arrangeGrob(plot_1, plot_2, plot_3,
                             plot_4, plot_5, plot_6,
                             plot_7, plot_8, plot_9,
                             ncol=3)
invisible(dev.off()); unlink(scratch_dev)

# Save high-resolution figure
dir.create("output", showWarnings = FALSE)
ggsave(
  filename = "output/FigureS1_training_performance.jpg",
  plot = combined_plot,
  width = 12,
  height = 12,
  dpi = 300,
  quality = 100,
  units = "in",
  scale = 1.5        # overall enlargement
)
