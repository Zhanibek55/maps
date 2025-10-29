-- DROP FUNCTION mapbuilder.check_x_y(point);

CREATE OR REPLACE FUNCTION mapbuilder.check_x_y(my_point point)
 RETURNS point
 LANGUAGE plpgsql
AS $function$  
  declare  
    out_point point := null; 
    wgs_bounds integer[] = array[45,85,37,57];
    gk9_bounds integer[] = array[9200000,9800000,4500000,6000000];
    gk10_bounds integer[] = array[10200000,10800000,4500000,6000000];
    gk11_bounds integer[] = array[11200000,11800000,4500000,6000000];
    gk12_bounds integer[] = array[12200000,12800000,4500000,6000000];
    sk66_bounds integer[] = array[11500000,12500000,3500000,4500000];
    gkN_bounds integer[] = array[200000,800000,4500000,6000000];
    
  begin   
    if my_point[0] > wgs_bounds[1] and my_point[0] < wgs_bounds[2] and my_point[1] > wgs_bounds[3] and my_point[1] < wgs_bounds[4] then
        out_point := my_point;
    elsif my_point[0] > gk9_bounds[1] and my_point[0] < gk9_bounds[2] and my_point[1] > gk9_bounds[3] and my_point[1] < gk9_bounds[4] then
        out_point := my_point;
    elsif my_point[0] > gk10_bounds[1] and my_point[0] < gk10_bounds[2] and my_point[1] > gk10_bounds[3] and my_point[1] < gk10_bounds[4] then
        out_point := my_point;
    elsif my_point[0] > gk11_bounds[1] and my_point[0] < gk11_bounds[2] and my_point[1] > gk11_bounds[3] and my_point[1] < gk11_bounds[4] then
        out_point := my_point;
    elsif my_point[0] > gk12_bounds[1] and my_point[0] < gk12_bounds[2] and my_point[1] > gk12_bounds[3] and my_point[1] < gk12_bounds[4] then
        out_point := my_point;
    elsif my_point[0] > sk66_bounds[1] and my_point[0] < sk66_bounds[2] and my_point[1] > sk66_bounds[3] and my_point[1] < sk66_bounds[4] then
        out_point := my_point;
    -- Setting cs_id by region
    elsif my_point[0] > gkN_bounds[1] and my_point[0] < gkN_bounds[2] and my_point[1] > gkN_bounds[3] and my_point[1] < gkN_bounds[4] then
        out_point := my_point;
    -- Changing X and Y coordinates 
    elsif my_point[1] > gk9_bounds[1] and my_point[1] < gk9_bounds[2] and my_point[0] > gk9_bounds[3] and my_point[0] < gk9_bounds[4] then
        out_point := (my_point[1], my_point[0]);
    elsif my_point[1] > gk10_bounds[1] and my_point[1] < gk10_bounds[2] and my_point[0] > gk10_bounds[3] and my_point[0] < gk10_bounds[4] then
        out_point := (my_point[1], my_point[0]);
    elsif my_point[1] > gk11_bounds[1] and my_point[1] < gk11_bounds[2] and my_point[0] > gk11_bounds[3] and my_point[0] < gk11_bounds[4] then
        out_point := (my_point[1], my_point[0]);
    elsif my_point[1] > gk12_bounds[1] and my_point[1] < gk12_bounds[2] and my_point[0] > gk12_bounds[3] and my_point[0] < gk12_bounds[4] then
        out_point := (my_point[1], my_point[0]);
        
    elsif my_point[1] > sk66_bounds[1] and my_point[1] < sk66_bounds[2] and my_point[0] > sk66_bounds[3] and my_point[0] < sk66_bounds[4] then
        out_point := (my_point[1], my_point[0]);
        
    end if;
    return out_point;
  end;  
  $function$
;





-- DROP FUNCTION mapbuilder.get_coord_system(point, text);

CREATE OR REPLACE FUNCTION mapbuilder.get_coord_system(my_point point, uwi text)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$  
  declare  
  cs_id int := null; 
  wgs_bounds integer[] = array[45,85,37,57];
  gk9_bounds integer[] = array[9200000,9800000,4500000,6000000];
  gk10_bounds integer[] = array[10200000,10800000,4500000,6000000];
  gk11_bounds integer[] = array[11200000,11800000,4500000,6000000];
  gk12_bounds integer[] = array[12200000,12800000,4500000,6000000];
  sk66_bounds integer[] = array[11500000,12500000,3500000,4500000];
  gkN_bounds integer[] = array[200000,800000,4500000,6000000];
  
  begin   
  if my_point[0] > wgs_bounds[1] and my_point[0] < wgs_bounds[2] and my_point[1] > wgs_bounds[3] and my_point[1] < wgs_bounds[4] then
      cs_id := 1;
  elsif my_point[0] > gk9_bounds[1] and my_point[0] < gk9_bounds[2] and my_point[1] > gk9_bounds[3] and my_point[1] < gk9_bounds[4] then
      cs_id := 3;
  elsif my_point[0] > gk10_bounds[1] and my_point[0] < gk10_bounds[2] and my_point[1] > gk10_bounds[3] and my_point[1] < gk10_bounds[4] then
      cs_id := 4;
  elsif my_point[0] > gk11_bounds[1] and my_point[0] < gk11_bounds[2] and my_point[1] > gk11_bounds[3] and my_point[1] < gk11_bounds[4] then
      cs_id := 5;
  elsif my_point[0] > gk12_bounds[1] and my_point[0] < gk12_bounds[2] and my_point[1] > gk12_bounds[3] and my_point[1] < gk12_bounds[4] then
      cs_id := 6;
  elsif my_point[0] > sk66_bounds[1] and my_point[0] < sk66_bounds[2] and my_point[1] > sk66_bounds[3] and my_point[1] < sk66_bounds[4] then
      cs_id := 7;
  -- Setting cs_id by region
  -- Because of intersection of Gauss-Kruger 9N, 10N, 11N, 12N ranges we check for another condition according to table above
  elsif my_point[0] > gkN_bounds[1] and my_point[0] < gkN_bounds[2] and my_point[1] > gkN_bounds[3] and my_point[1] < gkN_bounds[4] 
      and uwi like any('{AKG%, AIR%, AKD%, AKK%, ALA%, ASA%, ASH%, ATA%, ATB%, ATK%, BBK%, BEK%, BJR%, BLG%, BNS%, BTN%, BUR%, DMB%, DSK%, DSR%, ELZ%, ESB%, GRN%, 
                      IKN%, JET%, KAL%, KKL%, KKR%, KMB%, KNK%, KON%, KRK%, KRT%, KSG%, KSH%, KSM%, KZH%, LMN%, MKT%, MSB%, NBZ%, NRG%, OIM%, PRI%, RVN%, SAK%, 
                      SGZ%, SJB%, SKA%, STV%, TNU%, TSG%, TTR%, TZH%, UAZ%, UJE%, UKM%, UVK%, UVN%, UZK%, UZN%, UZS%, UZV%, VMT%, VOS%, ZBN%, ZHT%, ZPV%}')	then
      cs_id := 8;
  elsif my_point[0] > gkN_bounds[1] and my_point[0] < gkN_bounds[2] and my_point[1] > gkN_bounds[3] and my_point[1] < gkN_bounds[4] 
      and uwi like any('{ALB%, JLM%, KLR%, KNB%, KOZ%, KRA%, KSB%, KSC%, KTU%, LAK%, SKS%, STS%, STU%, STV%, SZK%, TLS%, UKM%, VMB%}')	then
      cs_id := 9;
  elsif my_point[0] > gkN_bounds[1] and my_point[0] < gkN_bounds[2] and my_point[1] > gkN_bounds[3] and my_point[1] < gkN_bounds[4] 
      and uwi like any('{AKH%, AKH%, AKH%, AKS%, AKS%, NUR%}')	then
      cs_id := 10;
  end if;
  return cs_id;
  end;  
  $function$
;




-- DROP FUNCTION mapbuilder.get_geometry(point, text);

CREATE OR REPLACE FUNCTION mapbuilder.get_geometry(my_point point, uwi text)
 RETURNS geometry
 LANGUAGE plpgsql
AS $function$  
  declare  
  res geometry := null;  
  my_system integer := mapbuilder.get_coord_system(my_point, uwi);
  begin  
    if my_system = 1 then 
        res := ST_SetSRID(ST_MakePoint(my_point[0], my_point[1]), 4326);
    elsif my_system = 3 then 
        res := ST_Transform(ST_SetSRID(ST_MakePoint(my_point[0], my_point[1]), 28409), 4326);
    elsif my_system = 4 then 
        res := ST_Transform(ST_SetSRID(ST_MakePoint(my_point[0], my_point[1]), 28410), 4326);
    elsif my_system = 5 then 
        res := ST_Transform(ST_SetSRID(ST_MakePoint(my_point[0], my_point[1]), 28411), 4326);
    elsif my_system = 5 then 
        res := ST_Transform(ST_SetSRID(ST_MakePoint(my_point[0], my_point[1]), 28412), 4326);
    elsif my_system = 7 then
        res := ST_Transform(ST_SetSRID(ST_MakePoint(my_point[0], my_point[1]), 420966), 4326);
    elsif my_system = 8 then
        res := ST_Transform(ST_SetSRID(ST_MakePoint(my_point[0], my_point[1]), 28469), 4326);
    elsif my_system = 9 then 
        res := ST_Transform(ST_SetSRID(ST_MakePoint(my_point[0], my_point[1]), 28470), 4326);
    elsif my_system = 10 then 
        res := ST_Transform(ST_SetSRID(ST_MakePoint(my_point[0], my_point[1]), 28471), 4326);
    end if;
    return res;
  end;  
  $function$
;

