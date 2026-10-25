export function localDate(value) {
  return String(value.getFullYear()).padStart(4,'0')+'-'+String(value.getMonth()+1).padStart(2,'0')+'-'+String(value.getDate()).padStart(2,'0');
}
export function parseDate(value) {
  if (!/^(?!0000)\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/.test(value)) return undefined;
  const [year,month,day]=value.split('-').map(Number), date=new Date(0);
  date.setFullYear(year,month-1,day);date.setHours(12,0,0,0);
  return localDate(date)===value?date:undefined;
}
export function validMonth(value) { return /^(?!0000)\d{4}-(0[1-9]|1[0-2])$/.test(value); }
export function addMonths(month, count) {
  const n=Number(month.slice(0,4))*12+Number(month.slice(5))-1+count;
  return String(Math.floor(n/12)).padStart(4,'0')+'-'+String(n%12+1).padStart(2,'0');
}
