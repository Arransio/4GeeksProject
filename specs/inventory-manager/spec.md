## CONTEXTO PREVIO
    Tomo como ejemplo items de un supermercado. 

INV-001: El sistema gestor de inventario debe calcular la cantidad de stock en función de los movimientos de entrada (albaranes de proveedores y devoluciones) y salida (ventas y merma) y modificar esos datos en la BBDD a través del endpoint especificado.

INV-002: El sistema gestor de inventario debe asegurar que el cálculo de stock deriva directamente de los movimientos registrados y no se edita directamente.

INV-003: El sistema gestor de inventario debe mantener el stock de forma que nunca puede ser negativo, siendo su número mínimo 0.

INV-004: El sistema gestor de inventario debe garantizar que un escaneo nunca equivale a más de un item.

EVT-001: cuando se reciba mercancía y se escanee una factura en la que vendrá especificado y verificado el número de cada item El sistema gestor de inventario debe registrar una entrada de mercancía.

EVT-002: cuando se procese una devolución a través de los escáneres de cajas El sistema gestor de inventario debe volver a sumar los items devueltos.

EVT-003: cuando las cajas registren la venta de productos El sistema gestor de inventario debe deducir estos productos de la cantidad de stock.

EVT-004: cuando se pase inventario a final de mes, donde se revisa si la cantidad de stock cuadra con la realidad El sistema gestor de inventario debe considerar los items desaparecidos como merma y sustraerlos de stock.

EXC-001: Si un movimiento dejase el stock en negativo entonces El sistema gestor de inventario debe bloquear el terminal y pedir credenciales de encargado para revisar el movimiento.

EXC-002: Si un movimiento manual dejase el stock en negativo entonces El sistema gestor de inventario debe bloquear el terminal y pedir credenciales de encargado para revisar el movimiento.