// samples/factorial.ml
// Calcula el factorial de un número de forma recursiva.
// Ejemplo representativo para el paper: demuestra funciones,
// condicionales y recursión — estructuras ricas para el AST.

func int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

func void main() {
    int numero = 10;
    int resultado = factorial(numero);
    print("factorial de ", numero, " es: ", resultado);
}
