# 05_aggregate_bootstrap_maps.R
#
# Step 5 of the workflow: per-pixel mean, standard deviation and relative standard deviation of
# the 100 bootstrap maps of one model and year, masked with the forest extent of that year.
#
# Same steps as the Earth Engine scripts gee/MLR_2005.js, gee/MLR_2015.js, gee/Cubist_2015.js and
# gee/RF_bootstrap_mean_sd_mask_template.js:
#
#   maps         <model>_<year>_1.tif .. <model>_<year>_100.tif  (written by 04_map_and_bootstrap_maps.R)
#   mean         ee.Reducer.mean()                       ->  <model>_<year>_mean.tif
#   SD           ee.Reducer.stdDev()                     ->  <model>_<year>_sd.tif
#   relative SD  100 * SD / mean (percent)               ->  <model>_<year>_rela_sd.tif
#   forest mask  CATCD tree cover of the same year, resampled bilinearly to the map grid, > 10 %
#                (manuscript section 2.1)                ->  <model>_<year>_{mean,sd,rela_sd}_mask.tif
#
# Standard deviation: ee.Reducer.stdDev() is the population SD (divisor n); sd() in R uses the
# sample SD (divisor n - 1). --sd selects one. The default is "sample"; for 100 maps the two
# differ by the factor sqrt(99 / 100) = 0.995.
# A pixel that is NA in any map is NA in the products (as with raster::calc; the Earth
# Engine reducers skip masked pixels image by image instead).
#
# Usage (from the package root)
#   Rscript 05_aggregate_bootstrap_maps.R --maps <folder> --model RF --year 2015 --out <folder> \
#       [--n 100] [--allow-missing] [--sd sample|population] \
#       [--mask <CATCD tree-cover GeoTIFF>] [--threshold 10] [--cores 4]
#
# --maps       folder with the bootstrap maps <model>_<year>_<k>.tif, k = 1..n (other files are ignored)
# --model      RF, MLR or Cubist (matched case-insensitively in the file names)
# --year       2005, 2015 or 2024
# --out        output folder
# --n          number of maps expected (default 100); the script stops when one is missing,
#              unless --allow-missing is given
# --sd         "sample" (default; sd() in R) or "population" (ee.Reducer.stdDev())
# --mask       tree-cover raster of the same year in percent (exported with gee/CATCD_treecover_export.js);
#              resampled bilinearly onto the map grid when the grids differ; pixels with cover
#              > --threshold are kept. For a 0 / 1 mask raster use --threshold 0.
# --threshold  percent tree cover (default 10)
# --cores      > 1 runs the mean and SD through raster::clusterR

suppressPackageStartupMessages(library(raster))

args <- commandArgs(trailingOnly = TRUE)
get_arg <- function(name, default = NULL) {
  i <- match(name, args); if (is.na(i) || i == length(args)) default else args[i + 1]
}
has_flag <- function(name) name %in% args

maps_dir  <- get_arg("--maps"); model <- get_arg("--model"); year <- get_arg("--year"); out_dir <- get_arg("--out")
n_maps    <- as.integer(get_arg("--n", "100"))
sd_type   <- match.arg(get_arg("--sd", "sample"), c("sample", "population"))
mask_file <- get_arg("--mask", NULL); threshold <- as.numeric(get_arg("--threshold", "10"))
n_cores   <- as.integer(get_arg("--cores", "1"))
allow_missing <- has_flag("--allow-missing")
if (is.null(maps_dir) || is.null(model) || is.null(year) || is.null(out_dir))
  stop("--maps, --model, --year and --out are required")

# 1. The maps: <model>_<year>_<k>.tif, k = 1..n ------------------------------------------------
all_tifs <- list.files(maps_dir, pattern = "\\.tif$", full.names = TRUE)
pat <- paste0("^", model, "_", year, "_([0-9]+)\\.tif$")
hits <- regmatches(basename(all_tifs), regexec(pat, basename(all_tifs), ignore.case = TRUE))
k <- vapply(hits, function(z) if (length(z) == 2) as.integer(z[2]) else NA_integer_, integer(1))
sel <- !is.na(k) & k >= 1 & k <= n_maps
tifs <- all_tifs[sel][order(k[sel])]; found <- sort(k[sel])
missing <- setdiff(seq_len(n_maps), found)
cat(sprintf("%s %s: %d of %d maps found in %s\n", model, year, length(found), n_maps, maps_dir))
if (length(missing)) {
  msg <- sprintf("missing map(s): %s", paste(missing, collapse = ", "))
  if (!allow_missing)
    stop(msg, " (use --allow-missing to aggregate the ", length(found), " maps that are there)")
  cat("WARNING:", msg, "- aggregating the maps that are there\n")
}
if (length(tifs) < 2) stop("need at least two maps")
maps <- stack(tifs)
n_used <- nlayers(maps)

# 2. Mean and SD, vectorised for raster::calc (x is a cells x maps matrix in the block path) ----
f_mean <- function(x) if (is.matrix(x)) rowMeans(x) else mean(x)
f_sd <- if (sd_type == "sample") {
  function(x) if (is.matrix(x)) { mu <- rowMeans(x); sqrt(rowSums((x - mu)^2) / (ncol(x) - 1)) } else sd(x)
} else {
  function(x) if (is.matrix(x)) { mu <- rowMeans(x); sqrt(rowSums((x - mu)^2) / ncol(x)) } else sqrt(mean((x - mean(x))^2))
}
run_calc <- function(fun) {
  if (n_cores > 1) {
    beginCluster(n_cores); on.exit(endCluster(), add = TRUE)
    clusterR(maps, calc, args = list(fun = fun))
  } else calc(maps, fun)
}

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
prefix <- file.path(out_dir, paste0(model, "_", year))
wr <- function(r, suffix) {
  f <- paste0(prefix, "_", suffix, ".tif")
  writeRaster(r, f, format = "GTiff", overwrite = TRUE, options = "COMPRESS=LZW"); cat("wrote", f, "\n"); r
}
mean_r <- wr(run_calc(f_mean), "mean")
sd_r   <- wr(run_calc(f_sd), "sd")
rela_r <- wr(overlay(sd_r, mean_r, fun = function(s, m) ifelse(m > 0, 100 * s / m, NA)), "rela_sd")

# 3. Forest mask: CATCD tree cover of the same year, bilinear, > threshold ----------------------
mask_note <- "no mask"
if (!is.null(mask_file)) {
  mk <- raster(mask_file)
  same_grid <- compareRaster(mk, mean_r, extent = TRUE, rowcol = TRUE, crs = TRUE, res = TRUE,
                             orig = TRUE, stopiffalse = FALSE)
  if (!same_grid) {
    if (!compareCRS(mk, mean_r)) stop("mask and maps are in different coordinate systems; reproject the mask first")
    cat("mask grid differs from the map grid: resampling bilinearly (as the Earth Engine scripts do)\n")
    mk <- resample(mk, mean_r, method = "bilinear")
  }
  forest <- calc(mk, function(v) ifelse(!is.na(v) & v > threshold, 1, NA))   # 1 = forest, NA elsewhere
  wr(mask(mean_r, forest), "mean_mask")
  wr(mask(sd_r,   forest), "sd_mask")
  wr(mask(rela_r, forest), "rela_sd_mask")
  mask_note <- sprintf("%s, tree cover > %s%s", mask_file, format(threshold),
                       if (same_grid) "" else " (resampled bilinearly onto the map grid)")
}

# 4. Log --------------------------------------------------------------------------------------
log_lines <- c(
  sprintf("05_aggregate_bootstrap_maps.R run on %s", format(Sys.time(), "%Y-%m-%d %H:%M")),
  sprintf("maps folder: %s", maps_dir),
  sprintf("maps used: %d of %d expected (%s_%s_<k>.tif)", n_used, n_maps, model, year),
  sprintf("missing: %s", if (length(missing)) paste(missing, collapse = ", ") else "none"),
  sprintf("standard deviation: %s (%s)", sd_type,
          if (sd_type == "sample") "divisor n - 1, sd() in R" else "divisor n, ee.Reducer.stdDev()"),
  sprintf("forest mask: %s", mask_note),
  sprintf("outputs: %s_{mean,sd,rela_sd%s}.tif", prefix,
          if (is.null(mask_file)) "" else ",mean_mask,sd_mask,rela_sd_mask"))
writeLines(log_lines, paste0(prefix, "_aggregation_log.txt"))
cat(paste(log_lines, collapse = "\n"), "\ndone\n")
