import { AbstractControl, ValidationErrors } from '@angular/forms';

/**
 * Valida CPF pelo dígito verificador (módulo 11).
 *
 * Aceita apenas 11 dígitos; máscaras são removidas antes da checagem.
 * Rejeita sequências repetidas (ex: `111.111.111-11`), que passam no cálculo
 * mas não são CPFs válidos.
 */
export function cpfValido(cpf: string): boolean {
  const digitos = cpf.replace(/\D/g, '');
  if (digitos.length !== 11 || /^(\d)\1{10}$/.test(digitos)) {
    return false;
  }

  const digitoVerificador = (base: string): number => {
    const soma = base
      .split('')
      .reduce((total, digito, indice) => total + Number(digito) * (base.length + 1 - indice), 0);
    const resto = soma % 11;
    return resto < 2 ? 0 : 11 - resto;
  };

  const primeiro = digitoVerificador(digitos.slice(0, 9));
  const segundo = digitoVerificador(digitos.slice(0, 10));
  return digitos[9] === String(primeiro) && digitos[10] === String(segundo);
}

/** Validator do Angular Forms: erro `cpfInvalido` quando o CPF não passa no checksum. */
export function cpfValidator(control: AbstractControl): ValidationErrors | null {
  const valor = control.value;
  if (typeof valor !== 'string' || valor.trim() === '') {
    return null;
  }
  return cpfValido(valor) ? null : { cpfInvalido: true };
}
