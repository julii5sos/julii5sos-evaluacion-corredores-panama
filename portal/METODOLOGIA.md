# Metodología del motor de conectividad · Cuenca del Canal + 10 km

## Área de estudio
Unión de las subcuencas de la Cuenca Hidrográfica del Canal de Panamá
(`Subcuencas_Canal_Panama.zip`) más una franja de amortiguamiento de 10 km.
Todo se calcula en UTM 17N (EPSG:32617), rejilla de 30 m (`motor/area.py`).

## Insumos (Google Earth Engine, `motor/gee.py`)
| Insumo | Fuente | Uso |
|---|---|---|
| Bosque por año | `GOOGLE/DYNAMICWORLD/V1`: clase modal *trees* y probabilidad media ≥ 0,5 | Fragmentación, pérdida y ganancia |
| Pérdida 2001–2025 | `UMD/hansen/global_forest_change_2025_v1_13` | Serie histórica y entrenamiento del riesgo |
| Alertas | Detector propio con `COPERNICUS/S1_GRD` (caída de VH ≥ 3 dB frente al mismo periodo del año anterior, en bosque) y RADD si cubre Panamá | Pérdida reciente |
| Altura de dosel | ETH Global Canopy Height 2020 (10 m) | Integridad estructural |
| Pendiente | `COPERNICUS/DEM/GLO30` | Estabilidad topográfica |
| Cauces perennes | `MERIT/Hydro/v1_0_1`, área de drenaje ≥ 1 km² | Proximidad riparia |
| KBA | ArcGIS `KBAs_LATAM_June2024` (`motor/kba.py`) | Priorización y contexto |

## Fragmentación y conectividad (`motor/fragstats.py`)
Métricas a nivel de clase (bosque), regla de 8 vecinos, como FRAGSTATS:
- **LPI**: % del área ocupado por el parche mayor.
- **ED**: m de borde bosque/no bosque por ha (sin contar el límite del área).
- **ENN_MN**: distancia media borde a borde al parche vecino más cercano.
- **CONNECT**: % de pares de parches a ≤ 300 m (`CONNECT_UMBRAL_M`).

Superficie continua para el ERI: en cada ventana de 1,5 km de radio
(`CONNECT_VENTANA_M`) se calcula la **conectividad equivalente** (ECA/A, %).
Es CONNECT ponderado por área: los parches a ≤ 300 m forman un componente,
ECA = √Σ A_k². Se usa en lugar de CONNECT puro porque CONNECT no está definido
cuando la ventana tiene un solo parche (por ejemplo, un bosque continuo). La
grilla gruesa se interpola a 30 m, que corresponde a la "interpolación espacial"
de la definición del ERI.

## ERI (`motor/pipeline.py`)
ERI = 0,35 × Integridad estructural + 0,25 × Conectividad + 0,20 × Estabilidad topográfica + 0,20 × Proximidad riparia

- **Integridad estructural**: 0,5 × altura de dosel / 35 m + 0,5 × área basal
  normalizada. Si se cargan parcelas de campo con área basal (`ab_m2ha`), un
  Random Forest con Sentinel-2 + altura la estima para todo el área. Sin
  parcelas, se usa como sustituto la probabilidad de árboles de Dynamic World.
- **Conectividad**: conectividad equivalente / 100.
- **Estabilidad topográfica**: 1 − (pendiente / 45°) × (1 − cobertura arbórea).
- **Proximidad riparia**: 1 − distancia al cauce perenne / 1 000 m.

Clases: > 0,75 alta (núcleos íntegros y estables), 0,40–0,75 media,
< 0,40 baja (fragmentado o modificado). Pesos y cortes están en `config.py`.

## Pérdida y riesgo de pérdida de conectividad
- **Pérdida de conectividad**: celdas donde la superficie de conectividad cayó
  más de 5 puntos entre el año base (2017) y el actual (`CAIDA_CONECTIVIDAD`).
- **Riesgo**: Random Forest (Earth Engine) entrenado con la pérdida Hansen de
  2020–2022 sobre el bosque de 2019. Los predictores son la distancia a pérdida
  reciente, al borde del bosque, a zona construida y a cauces, más la pendiente
  y la elevación. Se aplica al bosque actual con predictores actualizados.

## Prioridades de intervención
1. **Proteger**: bosque con ERI ≥ 0,6 y riesgo en el cuartil superior.
2. **Restaurar**: pasto, cultivo o arbusto en el 30 % superior de
   0,4 × proximidad riparia + 0,3 × pendiente + 0,3 × bosque vecino.
3. **Vigilar**: alertas recientes o pérdida de conectividad.

## Verificación de polígonos (`motor/verificar.py`)
El polígono (dibujado o subido, no se guarda) se envía a Earth Engine y se
calcula en vivo a 10 m:
- bosque por año;
- pérdida y ganancia en el periodo elegido;
- pérdida anual Hansen;
- alertas Sentinel-1 (y RADD si hay cobertura);
- LPI, CONNECT, ED, ENN y conectividad equivalente.

A eso se suman el ERI, el riesgo y las prioridades del último cálculo del motor,
y las KBA que toca el polígono. Sin Earth Engine se usan los rásters del motor.

## Limitaciones
- Dynamic World empieza en 2017 (mediados de 2015 en algunas zonas). Para años
  anteriores usar Hansen.
- La nubosidad reduce las observaciones ópticas. Por eso las alertas recientes
  se basan en radar.
- Los umbrales (300 m, 1,5 km, 3 dB, pesos del ERI) deben validarse con datos de
  campo de la cuenca.
- `motor/gee.py` se escribió sin poder ejecutarlo contra Earth Engine. Revisar
  los assets marcados con «VERIFICAR» en la primera corrida (o con
  `gee_code_editor.js`).
