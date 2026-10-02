# Manual de Operación y Mantenimiento — Bomba Centrífuga BX-200

Industrias Delta S.A.
Número de parte: DOC-BX200-ES-03
© Copyright 2024 Industrias Delta S.A. All rights reserved.
Todos los derechos reservados. Prohibida su reproducción total o parcial sin autorización escrita.
Delta y el logotipo Delta son marcas registradas de Industrias Delta S.A.
Disclaimer: la información de este documento puede cambiar sin previo aviso.

## Aviso legal

Este manual es propiedad de Industrias Delta S.A. Todas las marcas mencionadas pertenecen a sus respectivos dueños. Los datos técnicos se ofrecen sin garantía expresa ni implícita. Industrias Delta no se hace responsable por daños derivados del uso indebido del equipo. All rights reserved. Todos los derechos reservados. Prohibida su reproducción.

## Historial de revisiones

| Revisión | Fecha | Descripción |
|---|---|---|
| Rev A | 2021-03-10 | Versión inicial |
| Rev B | 2022-07-22 | Actualización de firmware 2.1 |
| Rev C | 2023-11-05 | Corrección de erratas |
| Rev D | 2024-02-18 | Nuevo procedimiento de arranque |

## Índice general

1. Introducción . . . . . . . . . . . . . . . . . . . . 5
2. Instalación . . . . . . . . . . . . . . . . . . . . 12
3. Operación . . . . . . . . . . . . . . . . . . . . 20
4. Mantenimiento . . . . . . . . . . . . . . . . . . . . 28
Apéndice A. Declaración de conformidad . . . . . . . . . . . . 40

## Lista de tablas

Tabla 1.1: Datos técnicos ........................................ 6
Tabla 4.1: Plan de mantenimiento ................................. 29
Tabla 4.2: Solución de problemas ................................. 33

## Índice de figuras

Figura 1.1: Vista explosionada . . . . . . . . . . . . 12
Figura 2.1: Esquema de conexión eléctrica . . . . . . . . . . . . 18

# Capítulo 1

INTRODUCCIÓN

## 1.1 Descripción general

La bomba centrífuga **BX-200** está diseñada para transferir agua limpia y fluidos ligeros en aplicaciones industriales. Su diseño de doble voluta permite un funcionamiento eﬁciente y estable incluso con caudales variables. El motor de inducción trifásico de 7,5 kW se acopla directamente al eje mediante un acople elástico, lo que reduce las vibraciones y prolonga la vida útil de los rodamientos.

Página 5 de 100

El equipo incorpora un sensor de temperatura en la carcasa y un sensor de presión en la descarga. Ambos envían sus lecturas al controlador principal, que ajusta la velocidad del motor para mantener el punto de trabajo. El controlador registra los últimos 500 eventos y los puede exportar por el puerto USB para su análisis posterior.

## Advertencia

PELIGRO: desconecte la corriente.

## 1.2 Datos técnicos

| Parámetro | Valor | Unidad |
|---|---|---|
| Caudal máximo | 120 | m³/h |
| Altura máxima | 45 | m |
| Potencia del motor | 7,5 | kW |
| Temperatura máxima del fluido | 80 | °C |
| Presión máxima de trabajo | 10 | bar |

El número de parte del kit de sellos es PART_NUMBER_A1 y debe solicitarse junto con el número de serie de la bomba. Los rodamientos cumplen ISO 9001 y el fabricante conserva el Copyright de los planos, pero eso no limita su uso en el mantenimiento normal del equipo.

# Capítulo 2

INSTALACIÓN

## 2.1 Preparación del sitio

Antes de instalar la bomba verifique que la base de concreto esté nivelada y que soporte el peso del equipo completo. La tubería de succión debe ser lo más corta posible y tener un diámetro igual o mayor al de la boca de succión. Evite codos cerrados cerca de la entrada, porque generan turbulencia y pueden provocar cavi-
tación. Instale una válvula de compuerta en la succión y una válvula de retención en la descarga.

Deje al menos un metro libre alrededor de la bomba para las tareas de inspección. El pro­cedimiento de nivelación debe repetirse después de conectar las tuberías, ya que la tensión de los tubos puede desalinear el acople.

## 2.2 Conexión eléctrica

Conecte los tres conductores de fase a los bornes **U, V y W** del motor y el conductor de tierra al borne marcado con el símbolo de tierra. Verifique que la tensión de la placa coincida con la de la red: 380 V trifásico. _Nunca_ conecte el motor con la caja de bornes abierta.

- 13 -

> Nota: revise el sentido de giro antes de acoplar el eje. Un giro invertido reduce el caudal a la mitad.

Configure el controlador con el archivo de parámetros:

```
PARAM_TEMP_MAX  =  80
PARAM_PRESION_MAX  =  10
```

El parámetro `PARAM_TEMP_MAX` define la temperatura límite en °C; si temp > 80°C el controlador detiene la bomba y muestra la alarma E-14.

## 2.3 Pruebas previas a la puesta en marcha

Antes de la primera puesta en marcha realice una prueba de aislamiento del motor con un megóhmetro de 500 V. El valor mínimo aceptable es de 10 MΩ entre cada fase y tierra. Si la lectura es menor, seque el bobinado y repita la medición. Verifique también que el eje gire libremente a mano y que el acople esté alineado con una tolerancia máxima de 0,05 mm. Registre los valores medidos en la bitácora de instalación para futuras comparaciones.

# Capítulo 3

OPERACIÓN

## 3.1 Arranque

El proce-
dimiento de arranque comienza con el llenado de la carcasa. Abra la válvula de succión, cierre la de descarga y purgue el aire por el tapón superior hasta que salga líquido sin burbujas. Encienda el motor y abra la válvula de descarga gradualmente hasta alcanzar el caudal de trabajo. No opere la bomba en seco: los sellos mecánicos se dañan en pocos segundos.

Durante los primeros diez minutos revise que no existan fugas en los sellos ni ruidos anormales. La presión en la descarga debe estabilizarse en el valor indicado en la tabla de datos técnicos.

## 3.2 Parada

Para detener la bomba cierre lentamente la válvula de descarga y apague el motor. Espere a que el eje se detenga por completo antes de cerrar la válvula de succión. Si la bomba va a permanecer parada más de una semana, drene la carcasa para evitar corrosión y congelamiento. Registre la hora de parada en la bitácora de operación junto con la lectura del sensor de presión.

## 3.3 Ajuste del sello mecánico

El sello mecánico se ajusta en fábrica y normalmente no requiere calibración. Si observa una fuga superior a diez gotas por minuto, detenga la bomba, cierre las válvulas y retire la protección del acople. Afloje los tornillos de la brida del sello y vuelva a apretarlos en cruz con un par de apriete de 25 Nm. Nunca apriete los tornillos con la bomba en marcha. Después del ajuste, abra las válvulas, arranque el motor y observe el sello durante al menos quince minutos antes de volver al servicio normal.

## Notas

Página en blanco.

# Capítulo 4

MANTENIMIENTO

## 4.1 Mantenimiento preventivo

| Tarea | Frecuencia |
|---|---|
| Revisar fugas en sellos mecánicos | Diaria |
| Lubricar rodamientos | Cada 2000 horas |
| Verificar alineación del acople | Cada 6 meses |
| Limpiar filtro de succión | Mensual |
| Revisar sensores de temperatura y presión | Anual |

Use grasa a base de litio para los rodamientos. No mezcle grasas de distinto tipo. Después de lubricar, gire el eje a mano para distribuir la grasa antes de arrancar el motor.

## 4.2 Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Alarma E-14 | Temperatura mayor a 80°C | Verificar caudal y enfriar la carcasa |
| Caudal bajo | Giro invertido del motor | Intercambiar dos fases |
| Ruido metálico | Rodamiento desgastado | Reemplazar rodamientos |
| Fuga en el eje | Sello mecánico dañado | Cambiar el kit PART_NUMBER_A1 |

Si el problema persiste después de aplicar la solución indicada, contacte al servicio técnico con el número de serie de la bomba y el código de alarma mostrado en el controlador.

## 4.3 Almacenamiento y transporte

Si la bomba va a almacenarse más de un mes, drene completamente la carcasa, aplique aceite protector en las superficies maquinadas y cubra las bocas de succión y descarga con tapas plásticas. Almacene el equipo en un lugar seco, con temperatura entre 5 y 40 °C y sin vibraciones. Gire el eje media vuelta cada mes para evitar que los rodamientos se marquen. Para el transporte utilice los cáncamos de elevación de la base y nunca levante la bomba por el motor ni por las tuberías.

## Apéndice A. Declaración de conformidad CE

Industrias Delta S.A. declara bajo su exclusiva responsabilidad que el producto descrito en este manual cumple las disposiciones de la Directiva 2006/42/CE (Máquinas), la Directiva 2014/30/UE (Compatibilidad electromagnética) y la Directiva 2011/65/UE (RoHS). Las normas armonizadas aplicadas son EN ISO 12100, EN 60204-1 y EN ISO 9906. La documentación técnica está disponible para las autoridades competentes. Esta declaración CE de conformidad pierde validez si el equipo se modifica sin autorización escrita del fabricante. Firmado en la sede de la empresa por el Director de Calidad.

## Apéndice B. Cumplimiento ambiental

El fabricante cumple el Reglamento REACH (CE) 1907/2006, la Directiva WEEE 2012/19/UE sobre residuos de aparatos eléctricos y la norma ISO 14001 de gestión ambiental. Los materiales de embalaje son reciclables y las sustancias restringidas se mantienen por debajo de los límites establecidos. Al final de su vida útil, el equipo debe entregarse a un gestor autorizado de residuos electrónicos.