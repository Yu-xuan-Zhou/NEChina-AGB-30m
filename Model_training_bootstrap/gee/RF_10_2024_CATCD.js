// Forest mask of 2024: tree cover of the China Annual Tree Cover Dataset (CATCD) 2024, bilinearly resampled,
// > 10 %; exported to the Drive folder RF_10_2024_CATCD.
/* This script facilitates the sharing and importation of the China Annual Tree Cover Dataset (CATCD) spanning the years 1985 to 2023.
   Creator: Yaotong Cai, PhD candidate, Sun Yat-sen University, caiyt33@mail2.sysu.edu.cn
*/
var mask=function(image,my_type){
  var mask = treeCanopyCover.gt(my_type);
  var masked_image=image.updateMask(mask);
  return masked_image;
}
var CATCD = ee.ImageCollection("projects/ee-caiyt33-catcd/assets/China_Annual_Tree_Cover_Dataset");
var treeCanopyCover = CATCD.filterDate('2024-01-01','2025-12-31').first().select('TreeCover')
                           .resample('bilinear').clip(table)
var RF_2024 = mask(treeCanopyCover,10)
Map.centerObject(RF_2024, 4)
// Map.addLayer(CATCD_2023.select('Uncertainty'),{min:0,max:20,palette:['white','red']},'2023 Uncertainty')
Map.addLayer(RF_2024,{min:10,max:100,palette:['white','black']},'2024 tree cover > 10 %')
Export.image.toDrive({

        image:RF_2024,

        description: 'RF_10_2024_CATCD',

        folder : 'RF_10_2024_CATCD',

        region: table,

        scale: 30,

        crs: "EPSG:4326",

        maxPixels: 1e13

      });
