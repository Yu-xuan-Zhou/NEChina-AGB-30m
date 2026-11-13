
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
AGB <- AGB[order(AGB$AGB), ]   # all plots, same order as 02_fit_models_70_30.R
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
      fit <- randomForest(x = traindata[, -1], y = traindata$AGB,
                          ntree = 500, mtry = max(floor((ncol(traindata) - 1) / 3), 1), importance = TRUE)
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
