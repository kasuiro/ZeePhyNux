
# ESTUDIO DE CASO EMPRESARIAL

**Sistema de información para la gestión de ventas, facturación y distribución de mercancías**

**1. Introducción**

Las empresas dedicadas a la comercialización y distribución de productos requieren mecanismos que les permitan controlar sus operaciones comerciales, administrar la información de sus clientes, registrar las ventas realizadas y garantizar que las mercancías lleguen correctamente a sus destinos.

Aunque para un cliente la compra de productos puede parecer una actividad sencilla, detrás de cada venta existe una secuencia de operaciones en la que intervienen diferentes personas, documentos, recursos físicos y procedimientos administrativos.

Un pedido realizado en un establecimiento comercial no constituye por sí solo la finalización de una venta. Es necesario que la empresa procese la solicitud, determine los artículos que serán facturados, genere el documento comercial correspondiente, prepare físicamente la mercancía y organice su transporte hasta el establecimiento del cliente.

Para comprender esta problemática, se presenta el caso de una empresa mayorista dedicada a comercializar y distribuir productos a diferentes tiendas y establecimientos comerciales de una ciudad y sus alrededores.

La empresa ha identificado tres subprocesos fundamentales dentro de su proceso general de ventas:

1. **Pedidos:** contacto comercial entre el vendedor y el cliente, mediante el cual se solicitan productos.
    
2. **Facturación:** procesamiento administrativo de las solicitudes comerciales y generación de las facturas correspondientes.
    
3. **Cargue:** preparación, organización y asignación de las mercancías facturadas a los vehículos responsables de su distribución.
    

Estos subprocesos se encuentran relacionados entre sí y requieren información consistente para garantizar el desarrollo adecuado de las operaciones.

El propósito del presente estudio es comprender su funcionamiento y establecer las bases para representar una parte de esta realidad empresarial mediante un modelo de datos relacional.

**2. Contexto general de la empresa**

La empresa cuenta con un portafolio de artículos destinados a la **venta al por mayor**. **Cada artículo dispone de un código** que permite identificarlo, **una descripción comercial**, un **precio de venta**, un **costo de adquisición** y un **porcentaje de impuesto al valor agregado (IVA)**, cuando corresponde.

**Sus principales compradores son tiendas de barrio**, **minimercados** y otros establecimientos comerciales que necesitan abastecerse periódicamente para mantener su actividad económica.

La organización dispone de un **grupo de vendedores** encargados de visitar los establecimientos comerciales, atender las **necesidades de los clientes** y **gestionar las solicitudes de mercancía.**

Para desarrollar sus actividades, los vendedores realizan recorridos por diferentes sectores de la ciudad, visitando numerosos establecimientos durante su jornada laboral.

Por su parte, la empresa dispone de personal **administrativo encargado de la facturación**, una **bodega donde se almacena** y **prepara la mercancía** y un conjunto de vehículos utilizados para realizar las **entregas**.

La distribución física está a **cargo de conductores y ayudantes**, quienes reciben los **cargues** preparados en la bodega y posteriormente realizan las **entregas** en las **direcciones** correspondientes.

El éxito de la operación depende de la **coordinación entre las actividades comerciales, administrativas y logísticas.**

**3. Primer subproceso: gestión de pedidos**

El proceso comercial comienza cuando **un vendedor visita los establecimientos** que forman parte de su recorrido de trabajo.

Durante una jornada puede atender **numerosos clientes**, cada uno con diferentes necesidades de abastecimiento.

Por ejemplo, un vendedor puede visitar una tienda que necesita **cinco unidades de un artículo**, **diez unidades de otro producto** y **veinte unidades adicionales de una tercera referencia.**

En otro establecimiento, el mismo vendedor puede recibir una **solicitud completamente diferente**, tanto en **productos como en cantidades**.

Cada cliente se encuentra **identificado mediante un código** y **dispone de información básica**, **como nombres**, **apellidos y dirección** del establecimiento o **dirección registrada para la atención comercial.**

El vendedor también posee un c**ódigo de identificación** que permite **reconocerlo dentro de la organización.**

Cuando el vendedor atiende a un cliente, **recibe la solicitud** de los **artículos requeridos** y **las cantidades** que el establecimiento desea adquirir.

**La solicitud puede contener un solo artículo** o **múltiples referencias comerciales**. Asimismo, **un mismo cliente puede solicitar mercancía en diferentes oportunidades**.

Al finalizar su recorrido, el **vendedor regresa a la empresa** o **transmite las solicitudes** a las personas encargadas de continuar el proceso comercial.

Es importante comprender que el pedido representa una **intención de compra** que debe ser procesada posteriormente por la empresa.

Por consiguiente, la **visita del vendedor** y la **r****ecepción de un pedido** no significan necesariamente que la **mercancía haya sido facturada o entregada.**

Desde el punto de vista de los sistemas de información, este subproceso permite identificar conceptos fundamentales: **vendedores**, **clientes,** **artículos** y **solicitudes de mercancía.**

**Alcance del ejercicio:** aunque los pedidos forman parte de la realidad empresarial, el modelo de datos entregado a los aprendices no contiene una tabla independiente denominada pedido. Por esta razón, el subproceso debe comprenderse como parte del contexto funcional, sin suponer que todos sus eventos quedan almacenados en la estructura suministrada.

**4. Segundo subproceso: facturación de mercancías**

Una vez que las solicitudes comerciales llegan a la empresa, comienza el proceso administrativo de facturación.

El personal responsable utiliza la información comercial para elaborar los documentos que respaldan las transacciones realizadas con los clientes.

Cada factura debe identificar el cliente al cual corresponde la operación, el vendedor relacionado con la transacción y la fecha de expedición del documento.

También es necesario registrar los diferentes artículos incluidos en la operación, las cantidades vendidas, los precios aplicados y los porcentajes de IVA correspondientes.

Por ejemplo, una factura puede contener las siguientes mercancías:

- Cinco unidades del artículo A.
    
- Diez unidades del artículo B.
    
- Veinte unidades del artículo C.
    

Aunque todos estos productos pertenecen a una misma operación comercial, cada referencia debe conservar su propia información de cantidad, precio e impuesto.

Esto significa que una factura constituye una unidad documental, pero su contenido puede estar conformado por varios artículos diferentes.

En consecuencia, debe diferenciarse la información general del documento de la información particular de cada producto facturado.

El sistema también contempla la existencia de documentos correspondientes a devoluciones de mercancía.

Para distinguir los tipos de transacciones, la empresa utiliza una codificación específica:

- **001:** factura de venta.
    
- **002:** devolución.
    

Por lo tanto, el número del documento debe interpretarse junto con el código de transacción que identifica su naturaleza.

Esta característica resulta especialmente importante porque permite gestionar diferentes documentos comerciales bajo una estructura común.

Adicionalmente, los valores registrados en el documento deben conservar las condiciones económicas de la operación realizada.

Por ejemplo, el precio de venta de un artículo puede cambiar con el tiempo. Sin embargo, una factura emitida anteriormente debe permitir consultar el precio efectivamente aplicado cuando se realizó aquella transacción.

Lo mismo sucede con los porcentajes de IVA y los costos asociados a los artículos, cuando estos datos se registran en el detalle de la operación.

Esta necesidad explica por qué algunos valores económicos aparecen tanto en la información general del artículo como en los registros correspondientes a los documentos facturados.

**Al finalizar el subproceso de facturación, la empresa dispone de documentos comerciales que identifican las mercancías que deberán ser preparadas para su posterior distribución.**

**5. Tercer subproceso: preparación y cargue de mercancías**

Después de la facturación, los documentos pasan al área de bodega, donde comienza el proceso de preparación física de los productos.

El personal de bodega recibe las facturas y las utiliza como referencia para identificar los artículos y cantidades que deben separarse del inventario físico.

Esta actividad es conocida habitualmente como alistamiento o preparación de pedidos.

Los operarios localizan los productos, verifican las cantidades y organizan la mercancía que posteriormente será distribuida a los distintos clientes.

Sin embargo, la empresa no utiliza necesariamente un vehículo diferente para cada factura.

Por el contrario, la operación logística requiere agrupar múltiples documentos comerciales dentro de una misma salida de distribución.

Para ello, la organización utiliza un mecanismo denominado **cargue**.

Un cargue representa una agrupación operativa de documentos comerciales cuya mercancía será transportada mediante un vehículo asignado.

Cada cargue se identifica mediante un número y dispone de información asociada a su preparación y distribución.

Por ejemplo, la empresa puede organizar el **cargue número 17**, conformado por 80 facturas correspondientes a diferentes clientes.

Estas facturas pueden contener numerosos artículos, diferentes cantidades y múltiples direcciones de entrega.

En este escenario, las 80 facturas forman parte de una sola operación de cargue, aunque cada una conserva su propia identidad documental y el detalle de los productos vendidos.

Esta distinción es fundamental: el cargue no reemplaza las facturas ni modifica el contenido comercial de cada una. Su finalidad es organizar y controlar el conjunto de documentos que participan en una operación de distribución.

La empresa puede preparar varios cargues durante una misma jornada, dependiendo de la cantidad de facturas pendientes, la disponibilidad de vehículos y la organización de los recorridos.

Asimismo, un vehículo puede ser utilizado en diferentes cargues a lo largo de su vida operativa, aunque cada cargue particular registra el vehículo asignado.

**6. Asignación del vehículo, conductor y ayudante**

Para realizar la distribución, la empresa dispone de vehículos identificados mediante códigos internos y descripciones que permiten reconocerlos.

También cuenta con conductores y ayudantes, quienes participan en las actividades de transporte y entrega de mercancías.

Una vez preparado un cargue, se establece el vehículo que transportará la mercancía y se asignan las personas responsables de realizar el recorrido.

El conductor tiene la responsabilidad de operar el vehículo y trasladar la mercancía hacia los establecimientos de destino.

El ayudante participa en las actividades de apoyo logístico, como la manipulación y descarga de los productos.

Retomando el ejemplo anterior, el cargue número 17 puede estar asignado a un vehículo de distribución, un conductor y un ayudante.

Ambos reciben las facturas correspondientes y la mercancía previamente preparada en la bodega.

A partir de este momento comienza la distribución física.

Durante el recorrido, el vehículo visita los diferentes establecimientos comerciales y entrega los artículos asociados a sus respectivas facturas.

Una misma operación de cargue puede implicar numerosas paradas y atención a clientes ubicados en diferentes sectores.

Por ello, el número de cargue permite agrupar y reconocer la operación logística, mientras que cada factura identifica una transacción comercial específica.

La información del conductor, ayudante y vehículo debe estar asociada con la operación de cargue para conocer los recursos asignados a la distribución.

**7. Entrega de las mercancías a los clientes**

Después de salir de la empresa, el conductor y el ayudante se desplazan hacia los establecimientos comerciales incluidos en el cargue.

En cada punto de entrega deben identificar la factura correspondiente y ubicar la mercancía destinada al cliente.

La factura permite verificar cuáles artículos fueron vendidos, qué cantidades se deben entregar y cuáles fueron las condiciones económicas registradas en la operación.

Por ejemplo, si el vehículo transporta mercancía asociada a 80 facturas, el personal debe distinguir los productos destinados a cada establecimiento para evitar errores durante el descargue.

Es posible que varios clientes se encuentren próximos entre sí, pero sus facturas y productos deben permanecer correctamente identificados.

Una vez terminada la distribución, la operación logística puede requerir procedimientos adicionales de cierre, conciliación de entregas, devolución de mercancías o reporte de novedades.

Estas actividades forman parte del funcionamiento habitual de una empresa distribuidora, pero no debe suponerse que todas están representadas en el modelo suministrado.

En particular, los estados y fechas registrados por el sistema deben interpretarse de acuerdo con las definiciones establecidas en el diccionario de datos y las reglas de negocio confirmadas por la organización.

**8. Integración de los tres subprocesos**

Los subprocesos de pedidos, facturación y cargue no funcionan de manera independiente.

Cada uno recibe información o resultados del anterior y participa en la continuidad de la operación comercial.

En el subproceso de pedidos se origina la necesidad de compra del cliente y se produce la intervención del vendedor.

En el subproceso de facturación se formaliza la transacción comercial mediante documentos que contienen la identificación del cliente, el vendedor, los artículos y las condiciones económicas correspondientes.

Finalmente, en el subproceso de cargue se organiza la mercancía facturada y se relacionan los documentos comerciales con los recursos logísticos utilizados en su distribución.

Así, una misma venta puede analizarse desde diferentes perspectivas.

Desde la perspectiva comercial, interesa conocer qué cliente adquirió determinados artículos y qué vendedor intervino.

Desde la perspectiva administrativa, interesa identificar el documento, la fecha, las cantidades y los valores registrados.

Desde la perspectiva logística, interesa establecer a qué cargue fue asignado el documento y cuáles fueron los recursos utilizados para transportar la mercancía.

La integración de estas perspectivas permite comprender por qué una base de datos empresarial requiere diferentes estructuras relacionadas entre sí.

**9. La importancia de la información en el sistema empresarial**

La empresa necesita que la información sea consistente y pueda consultarse desde distintas áreas.

Por ejemplo, la organización podría necesitar responder preguntas como las siguientes:

¿Qué facturas están asociadas a un determinado cliente?

¿Cuáles artículos aparecen registrados en una factura específica?

¿Qué vendedor está asociado a una operación comercial?

¿Cuántas facturas se encuentran relacionadas con el cargue número 17?

¿Qué vehículo, conductor y ayudante fueron asignados a un cargue?

¿Cuáles son los artículos y cantidades registrados en las facturas agrupadas dentro de un cargue?

¿Cuáles documentos corresponden a facturas y cuáles a devoluciones?

Para responder estas preguntas, no resulta suficiente almacenar información de manera aislada.

Es necesario establecer una estructura que permita identificar los registros y relacionar los datos correspondientes a clientes, vendedores, artículos, documentos y cargues.

También debe evitarse que las relaciones entre los registros dependan únicamente de coincidencias textuales o descripciones comerciales.

Los códigos y números de identificación cumplen una función importante, ya que permiten reconocer formalmente los diferentes elementos del sistema.

La calidad de la información depende de que estas identificaciones sean utilizadas correctamente y de que las relaciones entre los registros conserven su integridad.

**10. El diccionario de datos como instrumento para comprender el negocio**

Para apoyar el análisis, la empresa suministra un diccionario de datos con la descripción de la estructura utilizada por su sistema de información.

Este documento identifica las tablas que conforman la base de datos, los atributos que contiene cada una y sus características técnicas.

También incluye información sobre los tipos de datos, las claves primarias y las claves foráneas.

El diccionario debe utilizarse en conjunto con el presente estudio de caso.

Mientras el ensayo describe cómo funciona la organización, el diccionario muestra cómo se representa una parte de esa realidad mediante datos estructurados.

Es importante reconocer que no todas las actividades descritas en el proceso empresarial necesariamente disponen de una tabla específica.

De igual manera, una tabla puede representar un concepto que interviene en diferentes etapas del proceso.

Por ello, el ejercicio no consiste simplemente en dibujar las tablas del diccionario.

Los aprendices deberán interpretar la función que cumple cada estructura, comprender su participación dentro de la organización e identificar las relaciones necesarias para representar correctamente la información.

El análisis debe prestar especial atención a los documentos comerciales, a los artículos que los conforman y a los cargues que agrupan documentos para su distribución.

**11. Situación problemática**

La empresa considera indispensable disponer de una representación clara de la estructura de su sistema de información para comprender las relaciones entre las operaciones comerciales y logísticas.

Actualmente cuenta con información de clientes, vendedores, artículos, facturas, devoluciones, vehículos, conductores, ayudantes y cargues.

Sin embargo, necesita que los aprendices analicen cómo estos elementos interactúan dentro del proceso general de ventas.

Para ello, solicita construir e interpretar un Modelo Entidad-Relación que permita representar las estructuras y relaciones existentes en el diccionario de datos.

La representación debe contribuir a comprender cómo un vendedor puede intervenir en diferentes operaciones comerciales, cómo un cliente puede estar asociado a diferentes documentos, cómo un documento puede contener varios artículos y cómo un cargue puede agrupar numerosas facturas.

También debe permitir reconocer la función de los vehículos, conductores y ayudantes dentro de las operaciones de distribución.

El ejercicio deberá respetar las estructuras efectivamente suministradas, sin incorporar automáticamente entidades o atributos que no formen parte del modelo original.

Cuando se identifiquen procesos del negocio que no estén representados en la estructura de datos, esta situación deberá documentarse como una observación del análisis.

**12. Conclusión**

El funcionamiento de una empresa distribuidora demuestra que una venta es mucho más que una transacción económica entre un vendedor y un cliente.

Detrás de cada factura existe un conjunto de actividades comerciales, administrativas y logísticas que requieren coordinación e intercambio de información.

La visita del vendedor permite identificar las necesidades del cliente; la facturación formaliza la operación comercial, y el cargue organiza la distribución de la mercancía hacia los establecimientos.

Aunque estos subprocesos cumplen funciones diferentes, todos forman parte de una misma operación empresarial.

La información producida durante cada etapa debe conservar relaciones que permitan comprender el recorrido de los documentos y las mercancías dentro de la organización.

En este contexto, el diseño de bases de datos relacionales constituye una herramienta fundamental para representar la realidad del negocio, organizar los datos y garantizar su consistencia.

El verdadero desafío del ejercicio consiste en comprender primero el funcionamiento empresarial y posteriormente interpretar su representación mediante entidades, atributos, claves y relaciones.

De esta manera, el Modelo Entidad-Relación deja de ser únicamente un diagrama técnico y se convierte en una representación estructurada de las actividades de una organización.

![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAk0AAAACCAYAAABFa+jIAAAAAXNSR0IArs4c6QAAAFBJREFUWEdjbGho+M8wCkZDYDQERkNgcIXAAaBzHAaXk0ZdMxoCoyEwkkMgJMCDgfHKhROjjaaRnApG/T4aAoMzBEYbTYMzXkZdNRoCIzoEAHfGCNkEnC6iAAAAAElFTkSuQmCC)

**Actividad de análisis para los aprendices**

Después de leer el estudio de caso y revisar el diccionario de datos suministrado, los aprendices deberán desarrollar las siguientes actividades:

1. Identificar el proceso principal de la empresa y describir sus tres subprocesos.
    
2. Reconocer los actores que participan en cada subproceso y explicar sus responsabilidades.
    
3. Identificar las entidades representadas en el diccionario de datos y explicar su función dentro del negocio.
    
4. Analizar los atributos de cada entidad y establecer cuáles permiten identificar los registros de manera única.
    
5. Reconocer las claves primarias simples y compuestas, explicando su función.
    
6. Identificar las claves foráneas y determinar cómo permiten relacionar las diferentes estructuras del modelo.
    
7. Establecer las cardinalidades y, cuando corresponda, las condiciones de participación que puedan deducirse de las restricciones del modelo.
    
8. Construir el Modelo Entidad-Relación utilizando las tablas y atributos suministrados.
    
9. Explicar cómo se identifican las facturas y los artículos correspondientes a un cargue determinado.
    
10. Identificar actividades del proceso empresarial que no estén representadas directamente en las tablas y explicar las implicaciones de esta situación.
    

**Producto esperado:** Modelo Entidad-Relación del sistema, acompañado de una explicación técnica de las entidades, relaciones, cardinalidades y principales reglas de integridad identificadas.

**Material de apoyo:** Diccionario de datos del sistema de ventas, facturación y cargue de mercancías.