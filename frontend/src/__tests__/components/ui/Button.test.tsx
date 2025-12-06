import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '@/components/ui/Button';

describe('Button Component', () => {
  it('renders button with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    fireEvent.click(screen.getByText('Click me'));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);

    expect(screen.getByText('Disabled')).toBeDisabled();
  });

  it('applies primary variant by default', () => {
    render(<Button>Primary</Button>);

    const button = screen.getByText('Primary');
    expect(button).toHaveClass('bg-primary-600');
  });

  it('applies secondary variant when specified', () => {
    render(<Button variant="secondary">Secondary</Button>);

    const button = screen.getByText('Secondary');
    expect(button).toHaveClass('border');
    expect(button).toHaveClass('border-gray-300');
  });

  it('applies ghost variant when specified', () => {
    render(<Button variant="ghost">Ghost</Button>);

    const button = screen.getByText('Ghost');
    expect(button).toHaveClass('text-gray-600');
  });

  it('applies danger variant when specified', () => {
    render(<Button variant="danger">Danger</Button>);

    const button = screen.getByText('Danger');
    expect(button).toHaveClass('bg-red-600');
  });

  it('applies small size when specified', () => {
    render(<Button size="sm">Small</Button>);

    const button = screen.getByText('Small');
    expect(button).toHaveClass('px-3', 'py-1.5', 'text-sm');
  });

  it('applies medium size by default', () => {
    render(<Button>Medium</Button>);

    const button = screen.getByText('Medium');
    expect(button).toHaveClass('px-4', 'py-2');
  });

  it('applies large size when specified', () => {
    render(<Button size="lg">Large</Button>);

    const button = screen.getByText('Large');
    expect(button).toHaveClass('px-6', 'py-3', 'text-base');
  });

  it('shows loading spinner when loading is true', () => {
    render(<Button loading>Loading</Button>);

    const button = screen.getByText('Loading');
    expect(button).toBeDisabled();
    // Check for spinner animation class
    expect(button.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('is disabled when loading', () => {
    const handleClick = jest.fn();
    render(
      <Button loading onClick={handleClick}>
        Loading
      </Button>
    );

    fireEvent.click(screen.getByText('Loading'));
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('accepts custom className', () => {
    render(<Button className="custom-class">Custom</Button>);

    const button = screen.getByText('Custom');
    expect(button).toHaveClass('custom-class');
  });
});
