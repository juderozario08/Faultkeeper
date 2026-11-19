import styled from "@emotion/styled";
import { useTheme, type ThemePreference } from "../theme/ThemeContext";
import { color } from "../theme/tokens";

const OPTIONS: { value: ThemePreference; label: string; icon: string }[] = [
  { value: "light", label: "Light", icon: "☀" },
  { value: "dark", label: "Dark", icon: "☾" },
  { value: "system", label: "System", icon: "◐" },
];

const Group = styled.div`
  display: inline-flex;
  border: 1px solid ${color.border};
  border-radius: 6px;
  overflow: hidden;
`;

const Option = styled.button<{ active: boolean }>`
  border: 0;
  background: ${({ active }) => (active ? color.surfaceHover : "transparent")};
  color: ${({ active }) => (active ? color.text : color.textMuted)};
  font: inherit;
  font-size: 12px;
  padding: 4px 9px;
  cursor: pointer;
  &:hover {
    color: ${color.text};
  }
`;

export function ThemeToggle() {
  const { preference, setPreference } = useTheme();
  return (
    <Group role="radiogroup" aria-label="Theme">
      {OPTIONS.map((o) => (
        <Option
          key={o.value}
          role="radio"
          aria-checked={preference === o.value}
          active={preference === o.value}
          onClick={() => setPreference(o.value)}
          title={`${o.label} theme`}
        >
          <span aria-hidden>{o.icon}</span> {o.label}
        </Option>
      ))}
    </Group>
  );
}
