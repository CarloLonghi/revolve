library(ggplot2)
library(sqldf)
library(plyr)
library(dplyr)
library(trend)
library(purrr)
library(ggsignif)
library(stringr)
library(reshape)
library(viridis)

####  this example of parameterization compares multiple types of experiments using one particular season ###

#### CHANGE THE PARAMETERS HERE ####

base_directory2 <-paste('/storage/karine/alifej2021', sep='')

analysis = 'analysis/measures/eq'
output_directory = paste(base_directory2,'/',analysis ,sep='')

experiments_type = c("staticplane", "scaffeqinv", "scaffeq", "statictilted")

runs = list(
            c(1:20),
            c(1:20),
            c(1:20),
            c(1:20))

# methods are product of experiments_type VS environments and should be coupled with colors.
# make sure to define methods_labels in alphabetic order, and experiments_type accordingly
methods_labels =  c("1-Flat", '2-Inv Equal', '3-Equal', "4-Tilted")

experiments_type_colors = c('#FF00FF',
                            '#0000CD', 
                            '#228B22',
                            '#D2691E') 

#aggregations = c('min', 'Q25','mean', 'median', 'Q75','max')
aggregations = c( 'Q25', 'median', 'Q75')

gens = 100
pop = 100

#gens_box_comparisons = c(gens-1)
gens_box_comparisons = c(99)


measures_names = c(
  'displacement_velocity_hill',
  'head_balance',
  #'branching',
  #'branching_modules_count',
 # 'limbs',
  #'extremities',
 # 'length_of_limbs',
  #'extensiveness',
 # 'coverage',
  'joints',
  #'hinge_count',
  #'active_hinges_count',
  #'brick_count',
  #'touch_sensor_count',
  #'brick_sensor_count',
  'proportion',
  #'width',
  #'height',
  'absolute_size'#,
  #'sensors',
  #'symmetry',
  #'avg_period'#,
  #'dev_period',
  #'avg_phase_offset',
  #'dev_phase_offset',
  #'avg_amplitude',
  #'dev_amplitude',
 # 'avg_intra_dev_params',
  #'avg_inter_dev_params'#,
  #'sensors_reach',
  #'recurrence',
  #'synaptic_reception'
)

# add proper labels soon...
measures_labels = c(
  'Speed (cm/s)',
  'Balance',
  #'Branching',
  #'branching_modules_count',
 # 'Rel number of limbs',
  #'Number of Limbs',
 # 'Rel. Length of Limbs',
  #'Extensiveness',
  #'Coverage',
  'Rel. Number of Joints',
  #'hinge_count',
  #'active_hinges_count',
  #'brick_count',
  #'touch_sensor_count',
  #'brick_sensor_count',
  'Proportion',
  #'width',
  #'height',
  'Size'#,
  # 'Sensors',
 # 'Symmetry',
  #'Average Period'#,
  #'Dev Period',
  #'Avg phase offset',
  #'Dev phase offset',
  #'Avg Amplitude',
  #'Dev amplitude',
 # 'Avg intra dev params',
  #'Avg inter dev params'#,
  #'Sensors Reach',
  #'Recurrence',
  #'Synaptic reception'
)

more_measures_labels = c(
  #'Novelty (+archive)',
  'Novelty',
  'Fitness',
  'Number of slaves'
)

#### CHANGE THE PARAMETERS HERE ####


methods = c()
for (exp in 1:length(experiments_type))
{
    methods = c(methods, paste(experiments_type[exp], sep='_'))
}

measures_snapshots_all = NULL

for (exp in 1:length(experiments_type))
{
  for(run in runs[[exp]])
  {
 
      measures_snapshots = read.table(paste(base_directory2,paste(experiments_type[exp], run, "snapshots_full.tsv", sep='_'), sep='/'),
                               header = TRUE)
      
      for( m in 1:length(measures_names))
      {
        measures_snapshots[measures_names[m]] = as.numeric(as.character(measures_snapshots[[measures_names[m]]]))
      }

      measures_snapshots$run = run
      measures_snapshots$displacement_velocity_hill =   measures_snapshots$displacement_velocity_hill*100
      measures_snapshots$run = as.factor(measures_snapshots$run)
      measures_snapshots$method = paste(experiments_type[exp], sep='_')
      measures_snapshots$method_label =  methods_labels[exp]

      if ( is.null(measures_snapshots_all)){
        measures_snapshots_all = measures_snapshots
      }else{
        measures_snapshots_all = rbind(measures_snapshots_all, measures_snapshots)
      }
    
  }
}


fail_test = sqldf(paste("select method,run,generation,count(*) as c from measures_snapshots_all group by 1,2,3 having c<",pop," order by 4"))
measures_snapshots_all = sqldf("select * from measures_snapshots_all where cons_fitness IS NOT NULL")

measures_names = c(measures_names, more_measures_names)
measures_labels = c(measures_labels, more_measures_labels)

for( m in 1:length(more_measures_names)){
  measures_snapshots_all[more_measures_names[m]] = as.numeric(as.character(measures_snapshots_all[[more_measures_names[m]]]))
}



measures_averages_gens_1 = list()
measures_averages_gens_2 = list()

for (met in 1:length(methods))
{
  measures_aux = c()
  p <- c(0.25, 0.75)
  p_names <- map_chr(p, ~paste0('Q',.x*100, sep=""))
  p_funs <- map(p, ~partial(quantile, probs = .x, na.rm = TRUE)) %>%
    set_names(nm = p_names)

  query ='select run, generation'
  for (i in 1:length(measures_names))
  {
    query = paste(query,', avg(',measures_names[i],') as ', methods[met], '_',measures_names[i],'_mean', sep='')
    query = paste(query,', median(',measures_names[i],') as ', methods[met], '_',measures_names[i],'_median', sep='')
    query = paste(query,', min(',measures_names[i],') as ', methods[met], '_',measures_names[i],'_min', sep='')
    query = paste(query,', max(',measures_names[i],') as ', methods[met], '_',measures_names[i],'_max', sep='')
    measures_aux = c(measures_aux, measures_names[i])
  }
  query = paste(query,' from measures_snapshots_all
                where method="', methods[met],'" group by run, generation', sep='')
  inner_measures = sqldf(query)

  quantiles = data.frame(measures_snapshots_all %>%
                           filter(method==methods[met]) %>%
                           group_by(run, generation) %>%
                           summarize_at(vars(  measures_aux), funs(!!!p_funs)) )
  for (i in 1:length(measures_names)){
    for(q in c('Q25', 'Q75')){
      variable =  paste(measures_names[i], q, sep='_')
      names(quantiles)[names(quantiles) == variable] <- paste(methods[met], '_',variable, sep='')
    }
  }
  inner_measures = sqldf('select * from inner_measures inner join quantiles using (run, generation)')

  measures_averages_gens_1[[met]] = inner_measures

  inner_measures = measures_averages_gens_1[[met]]

  inner_measures$generation = as.numeric(inner_measures$generation)

  measures_aux = c()
  query = 'select generation'
  for (i in 1:length(measures_names))
  {
    query = paste(query,', median(', methods[met],'_',measures_names[i],'_mean) as ' , methods[met],'_',measures_names[i],'_mean_median', sep='')
    query = paste(query,', median(', methods[met],'_',measures_names[i],'_median) as ', methods[met],'_',measures_names[i],'_median_median', sep='')
    query = paste(query,', median(', methods[met],'_',measures_names[i],'_min) as ', methods[met],'_',measures_names[i],'_min_median', sep='')
    query = paste(query,', median(', methods[met],'_',measures_names[i],'_max) as ', methods[met],'_',measures_names[i],'_max_median', sep='')
    query = paste(query,', median(', methods[met],'_',measures_names[i],'_Q25) as ', methods[met],'_',measures_names[i],'_Q25_median', sep='')
    query = paste(query,', median(', methods[met],'_',measures_names[i],'_Q75) as ', methods[met],'_',measures_names[i],'_Q75_median', sep='')

    measures_aux = c(measures_aux, paste(methods[met],'_',measures_names[i],'_mean', sep='') )
    measures_aux = c(measures_aux, paste(methods[met],'_',measures_names[i],'_median', sep='') )
    measures_aux = c(measures_aux, paste(methods[met],'_',measures_names[i],'_min', sep='') )
    measures_aux = c(measures_aux, paste(methods[met],'_',measures_names[i],'_max', sep='') )
    measures_aux = c(measures_aux, paste(methods[met],'_',measures_names[i],'_Q25', sep='') )
    measures_aux = c(measures_aux, paste(methods[met],'_',measures_names[i],'_Q75', sep='') )
  }
  query = paste(query,' from inner_measures group by generation', sep="")
  outter_measures = sqldf(query)

  quantiles = data.frame(inner_measures %>%
                           group_by(generation) %>%
                           summarize_at(vars(  measures_aux), funs(!!!p_funs)) )

  measures_averages_gens_2[[met]] = sqldf('select * from outter_measures inner join quantiles using (generation)')

}


for (met in 1:length(methods))
{
  if(met==1){
    measures_averages_gens = measures_averages_gens_2[[1]]
  }else{
    measures_averages_gens = merge(measures_averages_gens, measures_averages_gens_2[[met]], all=TRUE, by = "generation")
  }
}


######

shapiro <- function(x){
  tryCatch(
    {
      y=round(shapiro.test(c(array(x))[[1]])$p.value,4)
      return(y)
    },
    error=function(error_message) {
      message(error_message)
      return(NA)
    }
  )
}




comps = list()
mlength = length(methods_labels)-1
idx=1
for (meto1 in 1:mlength)
{ aux = meto1+1
  for (meto2 in aux:length(methods_labels))
  {
    if (meto1!=meto2){
      comps[[idx]] = c(methods_labels[meto1], methods_labels[meto2])
      idx=idx+1
    }
  }
}

file <-file(paste(output_directory,'/normality.txt',sep=''), open="w")
all_na = colSums(is.na(measures_averages_gens)) == nrow(measures_averages_gens)

for (i in 1:length(measures_names))
{

  #  line plots


  # finding values for scaling
  max_y =  0
  min_y = 10000000
  for(a in 1:length(aggregations)){
    for(m in 1:length(methods)){
      max_value = max(measures_averages_gens[paste(methods[m],'_',measures_names[i],'_', aggregations[a], '_Q75',sep='')], na.rm = TRUE)
      min_value = min(measures_averages_gens[paste(methods[m],'_',measures_names[i],'_', aggregations[a], '_Q25',sep='')], na.rm = TRUE)
      if(max_value > max_y){ max_y = max_value }
      if(min_value < min_y){ min_y = min_value }
    }
  }
  #if (measures_names[i] == 'absolute_size' )  {    max_y = 16}

  for(a in 1:length(aggregations)){

    graph <- ggplot(data=measures_averages_gens, aes(x=generation))

    for(m in 1:length(methods)){

      is_all_na = all_na[paste(methods[m],'_',measures_names[i],'_', aggregations[a], '_median', sep='')]

      if (is_all_na == FALSE) {

        graph = graph + geom_ribbon(aes_string(ymin=paste(methods[m],'_',measures_names[i],'_', aggregations[a],'_Q25',sep=''),
                                               ymax=paste(methods[m],'_',measures_names[i],'_', aggregations[a],'_Q75',sep='') ),
                                    fill=experiments_type_colors[m], alpha=0.2, size=0)

        graph = graph + geom_line(aes_q(y = as.name(paste(methods[m],'_',measures_names[i],'_', aggregations[a], '_median', sep='')) ,
                                        colour=paste(methods_labels[m], aggregations[a], sep='_')), size=1)
      }
    }

    if (max_y>0) {
      graph = graph + coord_cartesian(ylim = c(min_y, max_y))
    }
    graph = graph  +  labs(y=measures_labels[i], x="Generation", title="")

    graph = graph +   scale_color_manual(values=experiments_type_colors)
    graph = graph  + theme(legend.position="none" ,  legend.text=element_text(size=25), axis.text=element_text(size=32), axis.title=element_text(size=30),
                           plot.subtitle=element_text(size=30 ), plot.title=element_text(size=30 ))

    # seasons markers
    graph = graph + geom_vline(xintercept = 17, linetype="dashed", color = "black",alpha=0.3)
    graph = graph + geom_vline(xintercept = 34, linetype="dashed", color = "black",alpha=0.3)
    graph = graph + geom_vline(xintercept = 51, linetype="dashed", color = "black",alpha=0.3)
    graph = graph + geom_vline(xintercept = 68, linetype="dashed", color = "black",alpha=0.3)
    graph = graph + geom_vline(xintercept = 85, linetype="dashed", color = "black",alpha=0.3)
     
    ggsave(paste( output_directory,'/',measures_names[i], '_', aggregations[a], '_lines.pdf',  sep=''), graph , device='pdf', height = 10, width = 10)



    # creates one box plot per measure, and one extra in case outlier removal is needeed
    outliers = c('full', 'filtered')
    for (out in outliers)
    {
      has_outliers = FALSE

      for(gc in gens_box_comparisons)
      {

        all_final_values = data.frame()
        for (met in 1:length(methods))
        {

          met_measures = measures_averages_gens_1[[met]]
          gen_measures = sqldf(paste("select * from met_measures where generation=", gc, sep=''))

          temp = data.frame( c(gen_measures[paste(methods[met],'_',measures_names[i],'_', aggregations[a], sep='')]))
          colnames(temp) <- 'val'

          if (out == 'filtered'){
            if (!all(is.na(temp$val))){

              num_rows_before = nrow(temp)
              upperl <- quantile(temp$val)[4] + 1.5*IQR(temp$val)
              lowerl <- quantile(temp$val)[2] - 1.5*IQR(temp$val)
              temp = temp %>% filter(val <= upperl & val >= lowerl )

              if (num_rows_before > nrow(temp)){
                has_outliers = TRUE
              }
            }
          }

          temp$type = methods_labels[met]
          all_final_values = rbind(all_final_values, temp)
        }
        
        
        if(a==2 && out == "full" && gc==99){
          mlength = length(methods_labels)-1
          for (meto1 in 1:mlength)
          { aux = meto1+1
            for (meto2 in aux:length(methods_labels))
            {
              if (meto1!=meto2){

                  set1=sqldf(paste("select val from all_final_values where type='",methods_labels[meto1],"'",sep=''))
                  set2=sqldf(paste("select val from all_final_values where type='",methods_labels[meto2],"'",sep=''))
          
                  s1=shapiro(set1['val'])
                  s2=shapiro(set2['val'])
                  
                  writeLines(paste(measures_names[i], 
                                   methods_labels[meto1], s1, 
                                   methods_labels[meto2], s2
                  ) , file)
              }
            }
          }
        }
        

        g1 <-  ggplot(data=all_final_values, aes(x= type , y=val, color=type )) +
          geom_boxplot(position = position_dodge(width=0.9),lwd=2,  outlier.size = 4) +
          labs( x="Method", y=measures_labels[i], title=str_to_title(aggregations[a]))

        g1 = g1 +  scale_color_manual(values=  experiments_type_colors  )

        g1 = g1 + theme(legend.position="none" , text = element_text(size=50) ,
                        plot.title=element_text(size=50),  axis.text=element_text(size=50),
                        axis.title=element_text(size=55),
                        axis.text.x = element_text(angle = 20, hjust = 0.9),
                        plot.margin=margin(t = 0.5, r = 0.5, b = 0.5, l =  1.3, unit = "cm"))+
          stat_summary(fun.y = mean, geom="point" ,shape = 16,  size=11)
        
        mxax = max(all_final_values[1])
        g1 = g1 + geom_signif( test="wilcox.test", size=1, textsize=15, #t.test
                               comparisons = comps,
                               map_signif_level=c("***"=0.001,"**"=0.01, "*"=0.05) , 
                               y_position=c(mxax*1.1, mxax*1.2, mxax*1.3, mxax*1.4, mxax*1.5, mxax*1.6)  )

        if (out == 'full' || (out == 'filtered' &&  has_outliers == TRUE) ){
          ggsave(paste(output_directory,"/",measures_names[i],"_",gc,"_", aggregations[a],'_', out,"_boxes.pdf",sep = ""), g1, device = "pdf", height=18, width = 10)
        }

      }

    }

  }

}

close(file)



