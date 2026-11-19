
# Objetivo:
Diseñar un entorno personalizado y adatable a diferentes situaciones, conservando la elegancia, apariencia, y vision del compositor de hyprland con wayland y alto rendimiento para diversas tareas, momentos y situaciones conservando desde arranque las configuraciones visuales de hyprland  para el usuario, con las siguientes caracteristicas en el UserConfig o donde corresponda la configuracion de cada bloque de tarea en este bloque con las nuevas sugerencias documentadas en la wiki oficial de hyprland con lua, y su arqutectura moderna optimizando en lo posible la utilizacion de los recursos.

# Programas - Ventanas - Terminal - Shell
*Cualquier ventana, programa y terminal debe conservar  y tener permanentemente lo siguiente al iniciar sesion/encender el equipo:
# Blur:
* Low Size: 3 Passes: 1 o en su defecto: off
# Opacity:
* 85%
# Fonts:
* Las fuentes deben adaptarse y ser legibles a los cambios dinamicos de color, blur y opacidad
* Las fuentes deben conservar un estilo adaptado a cada terminal
* En caso de no contar con las suficientes, preguntar si se desean instalar, y aconsejar cuales son las mas utiles para codigo, lectura, apariencia y estilo. 

# Imagenes - Terminales

*Se desea que cada que se abra una terminal cada una tenga una estructura definida y distinta, con lo siguiente:

* Cada terminal abierta dispondra de una imagen dinamica de personajes, stickers o memes en una cuadricula pequeña al lado; estilo parecido a lo que hace fastfetch
* Deberan ser asincronas para evitar conflictos entre cada imagen y terminal, dado que no se obtruya una imagen con otra, esto se hara creando una galeria de imagenes estaticas en la ruta donde se encuentran imagenes/wallpapers/
* El shell usado por defecto es fish 4.0.2
* Se deberan buscar, repositorios con galeria de imagenes gratuitas en la web, con alta calidad y estilo, o podrian implementarse formatos gift con awww
* El proposito es generar diferenciacion de terminales dinamicas cada una con su propio estilo y estructura.
* Buscar las mejores plataformas y descargar las imagenes o pasar el enlace para hacerlo
* Deben ser acetables formatos .svg, .png, gift o el mejor adatable a la configuracion en lua
* Revisar las configuraciones, estructura de archivos y arquitectura para entender y generar una mejor planeacion del proceso a realizar.
# Consideraciones:
* La version actual de Hyprland es la 0.55.2 (Wayland), en este sistema, revisa
* La version actual del sddm es la 0.21.0 (Wayland), en este sistema, revisa
* La version actual de kitty  es 0.41.1 en este sistema, revisa
* Llevar un check list de las del proceso de actividades y tareas completadas
* Revisar documentacion oficial, repositorios, y webs de ayuda en caso de necesitar conocer algo
* Informar del proceso y tarea completada
* Compactar el chat de ser necesario y ejecutar uno nuevo que continue el trabajo
* Las fuentes deben ser open source y de licencia abierta
* Si se considera que se puede actualizar hyprland, o si existe un compositor y gestor de ventanas mas optimo para este caso, recomendar para investigacion.
* Adjuntar fuentes de consulta, documentacion y repositorios con tools utiles.

# Personajes - memes - stickers - gifts - juegos - series - manga
*Las imagenes se centraran en imagenes, sticker  y gifts de lo siguiente:
* Shingeki no kiojin: Eren Jaeger, Mikasa ackerman, levi ackerman, annie leonheart, Sasha braus, Forma Titan de ataque, lewd mikasa, lewd eren, Ymir, gaby, historia, armin
* Berserk: guts, casca, grifit, puck, Judeau, Corkus, y Rickert, Void, Slan, Ubik, Conrad y Femto, el Conde, el Barón Serpiente, Zodd, Rosine, Wyald, Grunbeld, Locus, Irvine y Rakshas, Farnese, Serpico, Isidro y Schierke.
* Fate series: emiya shirou, arturia pendragon, merlin, medusa, rin tothsaka, sakura, astolfo, lancer, aquiles, enkidu, illya bon ainzbert, emiya kiritsugu,  - https://typemoon.fandom.com/es/wiki/Categor%C3%ADa:Personajes_en_Fate/stay_night
* Type moon: Tsukihime - Shiki Tohno, Arcueid Brunestud, Ciel, Akiha Tohno, Kohaku, y Hisui, neko arc
* Cyberpunk edgerunners anime: - [
    
    David Martínez
    
    
    
    ](https://cyberpunk.fandom.com/es/wiki/David_Mart%C3%ADnez)
- [
    
    ![Lucyna Kushinada](https://static.wikia.nocookie.net/cyberpunk/images/f/ff/Lucy_Infobox_CPEDGE.png/revision/latest/smart/width/160/height/120?cb=20230401170742&path-prefix=es)
    
    Lucyna Kushinada
    
    
    
    ](https://cyberpunk.fandom.com/es/wiki/Lucyna_Kushinada)
- [
    
    ![Rebecca](https://static.wikia.nocookie.net/cyberpunk/images/1/19/Rebecca_Infobox_CPEDGE.png/revision/latest/smart/width/160/height/120?cb=20230401040046&path-prefix=es)
    
    Rebecca
    
    
    
    ](https://cyberpunk.fandom.com/es/wiki/Rebecca)
- [
    
    ![Maine](https://static.wikia.nocookie.net/cyberpunk/images/f/fe/Maine_Infobox_CPEDGE.png/revision/latest/smart/width/160/height/120?cb=20230405201247&path-prefix=es)
    
    Maine
    
    
    
    ](https://cyberpunk.fandom.com/es/wiki/Maine)
- [
    
    ![Gloria Martínez](https://static.wikia.nocookie.net/cyberpunk/images/d/d9/Gloria_Infobox_CPEDGE.png/revision/latest/smart/width/160/height/120?cb=20230402125533&path-prefix=es)
    
    Gloria Martínez
    
    
    
    ](https://cyberpunk.fandom.com/es/wiki/Gloria_Mart%C3%ADnez)
- [
    
    ![Pilar](https://static.wikia.nocookie.net/cyberpunk/images/7/7b/Pilar_Infobox_CPEDGE.png/revision/latest/smart/width/160/height/120?cb=20230408002102&path-prefix=es)
    
    Pilar
    
    
    
    ](https://cyberpunk.fandom.com/es/wiki/Pilar)
- [
    
    ![Kiwi](https://static.wikia.nocookie.net/cyberpunk/images/6/6a/Kiwi_Infobox_CPEDGE.jpg/revision/latest/smart/width/160/height/120?cb=20230401044107&path-prefix=es)
    
    Kiwi
    
    
    
    ](https://cyberpunk.fandom.com/es/wiki/Kiwi)
- [
    
    ![Sasha Yakovleva](https://static.wikia.nocookie.net/cyberpunk/images/1/1e/Sasha_Infobox_CPEDGE.png/revision/latest/smart/width/160/height/120?cb=20230402134653&path-prefix=es)
    
    Sasha Yakovleva
    
    
    
    ](https://cyberpunk.fandom.com/es/wiki/Sasha_Yakovleva)
    
* Full metal Demon Muramasa: Kageaki Minato, quien es el protagonista, y Muramasa, que es su Tsurugi. Otros personajes importantes son Ichigo y Ginseigo
* Ergo proxy: Vincent Law/Ergo Proxy y Proxy One, Monad Proxy (también llamada Real), Re-L Mayer y su réplica Re-L2, Pino, Daedalus, Raúl Creed, Kristeva y Iggy.
* Doki doki literature club: Monica, sayori, 
* Goddes of victory nikke: crow, rapi, behemoth, marciana, red hood, elegg, gulty, marian, 
* Gantz:  Kei Kurono, Masaru Katō, Reika Shimohira, y Joichiro Nishi. Otros personajes notables son Tae Kojima, Ayumu Katō, y Yoshikazu Suzuki.
* Claymore manga: Clare, Teresa, y Priscilla
* FLCL: Naota Nandaba, Haruko Haruhara, y Mamimi Samejima. Otros personajes notables son Amarao y Canti.
* Homunculus manga:  Nakoshi Susumu, el protagonista, y Manabu Ito
* Lesson in love - visual novel: Akira, maya, rin, sana, kaori, yumi, chika, sekai, noriko, 
* To love ru - anime: To Love Ru y To Love Ru Darkness incluyen a Rito Yuuki, Lala Satalin Deviluke, y Haruna Sairenji. También son importantes Momo Belia Deviluke y Yami en la serie Darkness
* Ghost in the shell: Motoko Kusanagi, Daisuke Aramaki y los Tachikomas.
* Akira: aneda, Tetsuo y Akira. También destacan Kei y el Coronel Shikishima.
* Kimi ni todoke: Sawako Kuronuma, Shota Kazehaya, Ryu Sanada, y Chizuru Yoshida.
* Chainsawman: Makima, kobeni, denji,
* To aru majutsu no index: Touma Kamijo, Index, Mikoto Misaka
* Serial experiment lain: Lain Iwakura, Alice, Mitsuko, y Eiri Masami
* Neon genesis evangelion: Shinji Ikari, Rei Ayanami, Asuka Langley Soryu, Misato Katsuragi, y Gendo Ikari. Otros personajes importantes son Ritsuko Akagi, Kozo Fuyutsuki, y Ryoji Kaji.
* Blame! manga:  - [
    
    Killy
    
    
    
    ](https://blame.fandom.com/es/wiki/Killy)
- [
    
    ![Sanakan](https://static.wikia.nocookie.net/blame/images/7/7d/Sanakan_6.PNG/revision/latest/smart/width/160/height/120?cb=20111017151601&path-prefix=es)
    
    Sanakan
    
    
    
    ](https://blame.fandom.com/es/wiki/Sanakan)
- [
    
    ![Davine Lu Linvega](https://static.wikia.nocookie.net/blame/images/9/95/Davine_Lu_Linvega_3.JPG/revision/latest/smart/width/160/height/120?cb=20111030192333&path-prefix=es)
    
    Davine Lu Linvega
    
    
    
    ](https://blame.fandom.com/es/wiki/Davine_Lu_Linvega)
- [
    
    ![Cibo](https://static.wikia.nocookie.net/blame/images/a/aa/Cibo_01.jpg/revision/latest/smart/width/160/height/120?cb=20140321121624&path-prefix=es)
    
    Cibo
    
    
    
    ](https://blame.fandom.com/es/wiki/Cibo)
- [
    
    ![Dhomochevsky](https://static.wikia.nocookie.net/blame/images/f/f0/Dhomochevsky_1.jpg/revision/latest/smart/width/160/height/120?cb=20111018200817&path-prefix=es)
    
    Dhomochevsky
    
    
    
    ](https://blame.fandom.com/es/wiki/Dhomochevsky)
- [
    
    ![Pcell](https://static.wikia.nocookie.net/blame/images/9/94/Pcell_1.JPG/revision/latest/smart/width/160/height/120?cb=20111029223936&path-prefix=es)
    
    Pcell
    
    
    
    ](https://blame.fandom.com/es/wiki/Pcell)
- [
    
    ![Zuru](https://static.wikia.nocookie.net/blame/images/5/55/Zuru_Blame%21_movie.jpg/revision/latest/smart/width/160/height/120?cb=20180911010131&path-prefix=es)
    
    Zuru
    
    
    
    ](https://blame.fandom.com/es/wiki/Zuru)
- [
    
    ![General Femenina de Los Seres de Silicio](https://static.wikia.nocookie.net/blame/images/8/83/General_femenina_de_los_seres_de_silicio_1.png/revision/latest/smart/width/160/height/120?cb=20111031183934&path-prefix=es)
    
    General Femenina de Los Seres de Silicio
    
    
    
    ](https://blame.fandom.com/es/wiki/General_Femenina_de_Los_Seres_de_Silicio)

# Waybar layout 

*Implementar, buscar o instalar ya sea lo que estan en el sistema o descargando uno mas adecuado, moderno con arquitectura multiproposito avanzado, que mejore la personalizacion, optimizacion  y apariencia de esta configuracion.
1. Elegir, descargar o instalar el que mas se adapte a este equipo y sea minimalista pero muestre todo lo necesario que se necesite ver en el layout
2. Si en las configuraciones por defecto encuentras uno que consideres el mas optimo indica cual y por que
# Waybar style
*Implementar, buscar o instalar ya sea lo que estan en el sistema o descargando uno mas adecuado, moderno con arquitectura multiproposito avanzado, que mejore la personalizacion, optimizacion  y apariencia de esta configuracion.
1. Elegir, descargar o instalar el que mas se adapte a este equipo y sea minimalista pero muestre todo lo necesario que se necesite ver en el style
2. Si en las configuraciones encuentras en que consideras el mas optimo indica cual
# Se maximizara la eficiencia del "Gamemode"  distribuyendo modos de adaptabilidad con roles, tesoros, recompensas y puntos.

"Este apartado es una propuesta a largo plazo para darle al gamemode mas dinamismo, personalizacion y entretenimiento al entorno y ecosistema de esta maquina"
* Revisar posibles actualizaciones y mejoras en esta configuracion,  para ampliar la optimizacion del sistema cuando se este en este modo, ya sea para juegos, ver series, peliculas, desarrollar software, escribir, leer, gamedev, etc.
* Se podria crear el modo "Devmode" que sea especifico para el caso de desarrollo de software empresarial, de proyectos, de estudio, independiente, etc.
* Modo "Readmode" Para casos de lectura de cualquier indole
* Modo "Writemode" Para casos de escritura, redaccion, etc.
* Modo "GameDevmode" Para casos de desarrollo de videosjuegos
* Modo "3Dmode" Para casos de modelado 3D o 2.5D en mi caso
* Modo "AudioVisualmode" Para casos de produccion audio visual e ingenieria de sonido
* Modo "Planingmode" Para entorno empresarial de planeacion de proyectos, gestion de proyectos
# Rofi menu
* Arreglar la configuracion del rofi, algo en el chat "wallpapers animados" rompio en atajo por teclado por defecto configurado por hyprland, en caso de ya estar bien configurado ignora esta parte.
# Negativos
* No se deben generar mediante IA, u scripts.
* No deben ser inventados o alucinados.
* No debe tomar mas de 3 horas terminar esta personalizacion
* No deben ser de pesima calidad
* No debe sobreescribir configuraciones ya establecidas
* No se deben tomar decisiones sesgadas o supuestas
* No se permite reiniciar el compositor sin autorizacion
* No se permite eliminacion de configuraciones
* No se permite manipular archivos sin antes entender la arquitectura del mismo
* No se debe consumir recursos de cpu o igpu y ram
* No se permite ejecutar comandos sudo o rm -rf, explicar al usuario para que el mismo se encargue
