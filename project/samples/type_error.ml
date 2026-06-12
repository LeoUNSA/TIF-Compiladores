// samples/type_error.ml
// Programa SINTÁCTICAMENTE válido pero con errores SEMÁNTICOS.
// Sirve para demostrar los diagnósticos del analizador semántico
// y, a futuro, las explicaciones accesibles de la capa de IA.

func int doble(int n) {
    return n * 2;
}

func void main() {
    int x = "hola";          // tipo: string asignado a int
    float y = 3;             // sin coerción: int asignado a float
    bool ok = x + y;         // suma de tipos incompatibles → bool
    int z = doble(x, 5);     // aridad incorrecta + tipo de argumento
    print(indefinida);       // variable no declarada
    if (x) {                 // condición no booleana
        break;               // break fuera de un bucle
    }
}
