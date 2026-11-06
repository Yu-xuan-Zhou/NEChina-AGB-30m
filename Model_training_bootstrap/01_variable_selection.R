# 01_variable_selection.R
#
# Step 1 of the workflow: rank the candidate predictors and evaluate how many to keep.
# The final predictor sets are the tables in data/predictor_tables.
#
# Procedure (per year)
#   0. shuffle the plots once (set.seed(11)) and keep plots with 0 < AGB < 200 Mg ha-1
#   1. 10-fold cross-validation of a randomForest with ALL candidate predictors (baseline)
#   2. importance ranking: 1000 regression trees (rpart), each on a random 63.2 % subsample of
#      the plots and a random half of the predictors; mean rpart variable.importance
#   3. top-n curve: for n = 1..MAX_VARS fit randomForest on the n best-ranked predictors,
#      10-fold CV RMSE and R2; the choice was the n with the best CV score
#   4. the same top-n curve for four correlation rankings (Spearman, Kendall, distance, Pearson)
#   5. VIF of the linear model on the Pearson-ranked predictors (MLR candidate screening)
#   6. 10-fold CV of the final randomForest on the selected predictors
#
# Usage
#   Rscript 01_variable_selection.R [candidates.csv] [MAX_VARS] [N_TREES]
#   defaults: data/variable_selection/candidates_2015.csv, 21, 1000
# Output: output/variable_selection/<table name>_*.csv

suppressPackageStartupMessages({
  library(randomForest); library(rpart); library(correlation); library(car)
})

args <- commandArgs(trailingOnly = TRUE)
in_csv   <- if (length(args) >= 1) args[1] else "data/variable_selection/candidates_2015.csv"
MAX_VARS <- if (length(args) >= 2) as.integer(args[2]) else 21L
N_TREES  <- if (length(args) >= 3) as.integer(args[3]) else 1000L  # rpart draws
NFOLD    <- 10L
tag      <- tools::file_path_sans_ext(basename(in_csv))
out_dir  <- "output/variable_selection"; dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# ---- 0. data: AGB first, candidate predictors after it; drop identifiers ---------------
trainall <- read.csv(in_csv)
trainall <- trainall[, setdiff(colnames(trainall), c("ID", "id", "latitude", "longitude", "Latitude", "Longitude"))]
trainall <- trainall[, c("AGB", setdiff(colnames(trainall), "AGB"))]
trainall <- subset(trainall, AGB > 0 & AGB < 200)
trainall <- trainall[, colSums(is.na(trainall)) == 0]
set.seed(11)
trainall <- trainall[sample(nrow(trainall), nrow(trainall)), ]
varinames <- setdiff(names(trainall), "AGB")
MAX_VARS <- min(MAX_VARS, length(varinames))
cat(sprintf("%s: %d plots, %d candidate predictors\n", tag, nrow(trainall), length(varinames)))

# ---- helper: 10-fold CV of randomForest(AGB ~ .) on a data frame (fold = row index mod 10)
cv_rf <- function(df, seed = 1) {
  set.seed(seed)
  er <- matrix(nrow = NFOLD, ncol = 2, dimnames = list(NULL, c("rmse", "R2")))
  for (i in seq_len(NFOLD)) {
    sa <- (seq_len(nrow(df)) %% NFOLD) == (i - 1)
    model <- randomForest(AGB ~ ., df[!sa, ])
    p <- predict(model, df[sa, ])
    er[i, ] <- c(sqrt(mean((df[sa, "AGB"] - p)^2)), cor(df[sa, "AGB"], p)^2)
  }
  colMeans(er)
}
top_n_curve <- function(ranking, label) {
  res <- data.frame(ranking = label, n = seq_len(MAX_VARS), fold10_mean_rmse = NA_real_, fold10_mean_R2 = NA_real_)
  for (n in seq_len(MAX_VARS)) {
    res[n, 3:4] <- cv_rf(trainall[, c("AGB", names(ranking)[1:n])])
    cat(sprintf("  %s top-%d: RMSE %.2f R2 %.3f\n", label, n, res[n, 3], res[n, 4]))
  }
  res
}

# ---- 1. baseline CV with all predictors ---------------------------------------------------
base <- cv_rf(trainall, seed = 11)
cat(sprintf("baseline RF, all predictors: RMSE %.2f, R2 %.3f\n", base[1], base[2]))

# ---- 2. rpart importance over N_TREES random subsamples ----------------------------------
var_useful_imp <- data.frame(varinames)
set.seed(1)
for (i in seq_len(N_TREES)) {
  sub <- trainall[sample(nrow(trainall), nrow(trainall) * 0.632),
                  c("AGB", sample(varinames, length(varinames) * 0.5))]
  mo <- rpart(AGB ~ ., sub)
  imp_i <- mo$variable.importance[setdiff(mo$frame$var, "<leaf>")]
  var_useful_imp <- merge(var_useful_imp, data.frame(varinames = names(imp_i), imp_i), by = "varinames", all.x = TRUE)
}
var_useful_imp[is.na(var_useful_imp)] <- 0
imp <- apply(var_useful_imp[, -1, drop = FALSE], 1, mean); names(imp) <- var_useful_imp[, 1]
imp2 <- rev(sort(imp))
write.csv(data.frame(predictor = names(imp2), mean_rpart_importance = imp2),
          file.path(out_dir, paste0(tag, "_rpart_importance.csv")), row.names = FALSE)

# ---- 3. top-n curve on the rpart ranking ---------------------------------------------------
curves <- top_n_curve(imp2, "rpart")

# ---- 4. correlation rankings and their top-n curves ---------------------------------------
cor_rank <- function(method) {
  r <- sapply(varinames, function(v) summary(correlation(trainall[, c(v, "AGB")], method = method))[1, 2])
  rev(sort(r))
}
rankings <- list()
for (m in c("spearman", "kendall", "distance", "pearson")) {
  rk <- tryCatch(cor_rank(m), error = function(e) { cat("  ", m, "ranking failed:", conditionMessage(e), "\n"); NULL })
  if (is.null(rk)) next
  rankings[[m]] <- rk
  write.csv(data.frame(predictor = names(rk), correlation = rk),
            file.path(out_dir, paste0(tag, "_", m, "_ranking.csv")), row.names = FALSE)
  curves <- rbind(curves, top_n_curve(rk, m))
}
write.csv(curves, file.path(out_dir, paste0(tag, "_top_n_curves.csv")), row.names = FALSE)

# ---- 5. VIF screening for the linear model (Pearson-ranked, min-max scaled) ---------------
if (!is.null(rankings$pearson)) {
  mx <- apply(trainall, 2, max); mn <- apply(trainall, 2, min)
  scaled <- as.data.frame(scale(trainall, center = mn, scale = mx - mn))
  vif_rows <- list()
  for (n in 2:MAX_VARS) {
    fit <- lm(AGB ~ ., data = scaled[, c("AGB", names(rankings$pearson)[1:n])])
    # perfectly collinear sets (e.g. HHVV_sum = HH + HV) have aliased coefficients and no VIF
    v <- tryCatch(car::vif(fit), error = function(e) setNames(rep(NA_real_, n), names(rankings$pearson)[1:n]))
    vif_rows[[length(vif_rows) + 1]] <- data.frame(n = n, predictor = names(v), vif = as.numeric(v),
                                                   adj_r2 = summary(fit)$adj.r.squared)
  }
  write.csv(do.call(rbind, vif_rows), file.path(out_dir, paste0(tag, "_vif_pearson.csv")), row.names = FALSE)
}

# ---- 6. selected set (rpart ranking, n with the highest CV R2) and its CV ------------------
rp <- curves[curves$ranking == "rpart", ]
n_best <- rp$n[which.max(rp$fold10_mean_R2)]
select_vari <- names(imp2)[1:n_best]
final <- cv_rf(trainall[, c("AGB", select_vari)])
cat(sprintf("selected %d predictors (rpart ranking, best CV R2): %s\n  final 10-fold CV: RMSE %.2f, R2 %.3f\n",
            n_best, paste(select_vari, collapse = ", "), final[1], final[2]))
write.csv(data.frame(rank = seq_along(select_vari), predictor = select_vari),
          file.path(out_dir, paste0(tag, "_selected_predictors.csv")), row.names = FALSE)
cat("done\n")
