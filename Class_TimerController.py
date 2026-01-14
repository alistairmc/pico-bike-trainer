import utime


class TimerController:
    """Timer controller class for managing timer functionality.
    
    This class handles timer state, elapsed time tracking, and timer operations.
    Separates timer business logic from input handling (MVC pattern).
    """
    
    def __init__(self):
        """Initialize the timer controller."""
        self.timer_state = 'stopped'  # 'stopped', 'running', 'paused'
        self.timer_elapsed_ms = 0  # Total elapsed time in milliseconds
        self.timer_start_time = 0  # When timer started running (for current run)
    
    def start(self, current_time):
        """Start the timer.
        
        Args:
            current_time: Current time in milliseconds.
        """
        if self.timer_state == 'stopped':
            self.timer_state = 'running'
            self.timer_start_time = current_time
            self.timer_elapsed_ms = 0
            print("Timer started")
        elif self.timer_state == 'paused':
            # Resume from paused state
            self.timer_state = 'running'
            self.timer_start_time = current_time
            print(f"Timer resumed from {self.format_time(self.timer_elapsed_ms)}")
    
    def pause(self, current_time):
        """Pause the timer.
        
        Args:
            current_time: Current time in milliseconds.
        """
        if self.timer_state == 'running':
            self.timer_state = 'paused'
            # Add elapsed time since start to total
            elapsed_since_start = utime.ticks_diff(current_time, self.timer_start_time)
            self.timer_elapsed_ms += elapsed_since_start
            print(f"Timer paused at {self.format_time(self.timer_elapsed_ms)}")
    
    def reset(self):
        """Reset the timer to 00:00.
        
        Only works when timer is paused.
        """
        if self.timer_state == 'paused':
            self.timer_state = 'stopped'
            self.timer_elapsed_ms = 0
            print("Timer reset")
    
    def get_elapsed_ms(self, current_time):
        """Get current timer elapsed time in milliseconds.
        
        Args:
            current_time: Current time in milliseconds.
            
        Returns:
            Elapsed time in milliseconds.
        """
        if self.timer_state == 'stopped':
            return 0
        elif self.timer_state == 'paused':
            return self.timer_elapsed_ms
        elif self.timer_state == 'running':
            elapsed_since_start = utime.ticks_diff(current_time, self.timer_start_time)
            return self.timer_elapsed_ms + elapsed_since_start
        return 0
    
    def get_state(self):
        """Get current timer state.
        
        Returns:
            Timer state string: 'stopped', 'running', or 'paused'.
        """
        return self.timer_state
    
    def format_time(self, elapsed_ms):
        """Format timer elapsed time as MM:SS string.
        
        Args:
            elapsed_ms: Elapsed time in milliseconds.
            
        Returns:
            Formatted time string (e.g., "05:23").
        """
        total_seconds = elapsed_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
