import {ChevronsUpDown} from 'lucide-react';

const hours = Array.from({length: 24}, (_, hour) => String(hour).padStart(2, '0') + ':00');

export function HourPicker({value, disabled, onChange}: {
  value: string;
  disabled: (hour: string) => boolean;
  onChange: (hour: string) => void;
}) {
  return <label className="hour-field">
    Boʻsh vaqt
    <span className="hour-control">
      <select value={value} onChange={event => onChange(event.target.value)}>
        <option value="">Istalgan vaqt</option>
        {hours.filter(hour => !disabled(hour)).map(hour =>
          <option key={hour} value={hour}>{hour}</option>
        )}
      </select>
      <ChevronsUpDown size={15} aria-hidden="true"/>
    </span>
  </label>;
}
