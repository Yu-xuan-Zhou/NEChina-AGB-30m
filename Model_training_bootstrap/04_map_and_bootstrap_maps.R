# 04_map_and_bootstrap_maps.R
#
# Step 4 of the workflow: apply a model to the predictor rasters and write one AGB map per
# repeat. Logic:
#
#   read the predictor table, keep plots with 0 < AGB < 200 Mg ha-1, set.seed(11), then for
#   repeat k: run k times {createDataPartition(p = 0.7); fit the model on the 70 % part}, and
#   predict the raster stack with the model of the k-th split -> <model>_<year>_<k>.tif
#
# Running k = 1..100 therefore gives the 100 bootstrap maps that were later averaged
# (05_aggregate_bootstrap_maps.R or the Earth Engine scripts in gee/); the RF 2015 map is the
# map of split 5.
#
# Model calls:
#   RF     randomForest(x = train[,-1], y = train$AGB, importance = TRUE)   (defaults: ntree 500)
#   MLR    stepAIC(lm(AGB ~ ., train), direction = "backward") in the loop, but the MAP was
#          made with a fixed-variable lm fitted on the k-th training set (option --formula);
#          the production runs used
#            2015: AGB ~ NDVI + NDWI + HH + HV + HV_savg + slope
#            2005: AGB ~ NDVI + MSAVI + B3 + slope + HH + HH_dent + HH_ent + HV_asm
#          Without --formula the stepAIC model of the k-th split is used.
#   Cubist cubist(x = train[,-1], y = train$AGB, committees = 10)
#
# Usage
#   Rscript 04_map_and_bootstrap_maps.R --model RF --year 2015 \
#       --table data/predictor_tables/RF/Landsat+Palsar/2015.csv \
#       --rasters I:/predictors_2015 --out I:/bootstrap_maps/RF_2015 \
#       [--first 1] [--last 100] [--cores 4] [--formula "AGB ~ NDVI + NDWI + HH + HV + HV_savg + slope"]
#
# Rasters: one GeoTIFF per predictor named <column>.tif in --rasters, all on the same grid.
# If the names differ (the 2015 production stack used SR3.tif for column B3, SR4.tif for B4,
# SR5.tif for B5, Slope.tif for slope), put a two-column csv `raster_names.csv`
# (column,file) in the raster folder. Outputs are LZW-compressed GeoTIFFs.

suppressPackageStartupMessages({
  library(randomForest); library(caret); library(Cubist); library(MASS); library(raster)
})

# ---- arguments -------------------------------------------------------------------------
args <- commandArgs(trailingOnly = TRUE)
get_arg <- function(name, default = NULL) {
  i <- match(name, args); if (is.na(i) || i == length(args)) return(default)
  # take every token up to the next "--flag" so that an unquoted formula also works
  j <- i + 1; while (j < length(args) && !startsWith(args[j + 1], "--")) j <- j + 1
  paste(args[(i + 1):j], collapse = " ")
}
model     <- match.arg(get_arg("--model"), c("RF", "MLR", "Cubist"))
year      <- get_arg("--year")
table_csv <- get_arg("--table")
ras_dir   <- get_arg("--rasters")
out_dir   <- get_arg("--out")
first_k   <- as.integer(get_arg("--first", "1"))
last_k    <- as.integer(get_arg("--last", "100"))
n_cores   <- as.integer(get_arg("--cores", "1"))
mlr_formula <- get_arg("--formula", NULL)
if (any(sapply(list(year, table_csv, ras_dir, out_dir), is.null)))
  stop("--year, --table, --rasters and --out are required")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# ---- data ------------------------------------------------------------------------------
AGB <- as.data.frame(read.csv(table_csv))
AGB <- subset(AGB, AGB > 0 & AGB < 200)
predictors <- setdiff(colnames(AGB), "AGB")
cat(sprintf("%s %s: %d plots, predictors: %s\n", model, year, nrow(AGB), paste(predictors, collapse = ", ")))

# ---- raster stack (layer names = table columns) ----------------------------------------
name_map <- file.path(ras_dir, "raster_names.csv")
files <- if (file.exists(name_map)) {
  nm <- read.csv(name_map, stringsAsFactors = FALSE)
  setNames(file.path(ras_dir, nm$file), nm$column)[predictors]
} else setNames(file.path(ras_dir, paste0(predictors, ".tif")), predictors)
missing <- files[!file.exists(files)]
if (length(missing)) stop("predictor rasters not found: ", paste(missing, collapse = ", "))
layers <- lapply(predictors, function(p) { r <- raster(files[[p]]); names(r) <- p; r })
vari <- stack(layers)

# ---- model of split k ------------------------------------------------------------------
fit_split <- function(k) {
  set.seed(11)
  for (i in seq_len(k)) {
    trains <- createDataPartition(y = AGB$AGB, p = 0.7, list = FALSE)
    traindata <- AGB[trains, ]
    if (model == "RF") {
      fit <- randomForest(x = traindata[, -1], y = traindata$AGB, importance = TRUE)
    } else if (model == "MLR") {
      fit <- stepAIC(lm(AGB ~ ., data = traindata), direction = "backward", trace = 0)
    } else {
      fit <- cubist(x = traindata[, -1], y = traindata$AGB, committees = 10)
    }
  }
  if (model == "MLR" && !is.null(mlr_formula))
    fit <- lm(as.formula(mlr_formula), data = traindata)   # fixed-variable map model of the production runs
  fit
}

predict_stack <- function(fit) {
  if (n_cores > 1) {
    beginCluster(n_cores)
    on.exit(endCluster(), add = TRUE)
    clusterR(vari, raster::predict, args = list(model = fit, type = "response"))
  } else {
    raster::predict(vari, fit, type = "response")
  }
}

for (k in seq(first_k, last_k)) {
  fit <- fit_split(k)
  out <- file.path(out_dir, sprintf("%s_%s_%d.tif", model, year, k))
  map <- predict_stack(fit)
  writeRaster(map, filename = out, format = "GTiff", overwrite = TRUE, options = "COMPRESS=LZW")
  cat(sprintf("repeat %d -> %s\n", k, out))
}
cat("done\n")
