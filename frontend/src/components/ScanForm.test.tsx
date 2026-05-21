import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithI18n } from "../test/render";
import { ScanForm } from "./ScanForm";

function setup(overrides: Partial<Parameters<typeof ScanForm>[0]> = {}) {
  const props = {
    target: "",
    setTarget: vi.fn(),
    apiKey: "",
    setApiKey: vi.fn(),
    remember: false,
    setRemember: vi.fn(),
    pivot: false,
    setPivot: vi.fn(),
    loading: false,
    error: "",
    onScan: vi.fn(),
    ...overrides,
  };
  renderWithI18n(<ScanForm {...props} />);
  return props;
}

describe("ScanForm", () => {
  it("renders the scan button", () => {
    setup();
    expect(screen.getByRole("button", { name: /scan/i })).toBeInTheDocument();
  });

  it("calls onScan when the button is clicked", async () => {
    const props = setup();
    await userEvent.click(screen.getByRole("button", { name: /scan/i }));
    expect(props.onScan).toHaveBeenCalledOnce();
  });

  it("calls onScan when Enter is pressed in the target field", async () => {
    const props = setup();
    await userEvent.type(screen.getByPlaceholderText(/domain/i), "x{Enter}");
    expect(props.onScan).toHaveBeenCalled();
  });

  it("disables the button and shows a label while scanning", () => {
    setup({ loading: true });
    expect(screen.getByRole("button", { name: /scanning/i })).toBeDisabled();
  });

  it("shows an error message", () => {
    setup({ error: "boom" });
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("toggles the remember-key option", async () => {
    const props = setup();
    await userEvent.click(screen.getByRole("checkbox", { name: /remember/i }));
    expect(props.setRemember).toHaveBeenCalledWith(true);
  });

  it("updates the target on input", async () => {
    const props = setup();
    await userEvent.type(screen.getByPlaceholderText(/domain/i), "a");
    expect(props.setTarget).toHaveBeenCalled();
  });
})
