// samples/control_flow.ml
// Demuestra while, for, break y continue.
// Útil para mostrar generación de CFG en el paper.

func int suma_pares(int limite) {
    int suma = 0;
    int i = 0;
    while (i <= limite) {
        if (i % 2 != 0) {
            i += 1;
            continue;
        }
        suma += i;
        i += 1;
    }
    return suma;
}

func void main() {
    // Sumar pares del 0 al 10
    int resultado = suma_pares(10);
    print("Suma de pares 0..10 = ", resultado);

    // for clásico con break
    int j = 0;
    for (int k = 0; k < 5; k += 1) {
        if (k == 3) {
            break;
        }
        print("k = ", k);
    }
}
