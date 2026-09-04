from enum import Enum, auto

class TeacherState(Enum):
    UNDERSTAND = auto()      # Process input, setup context
    PLAN = auto()            # Generate lesson plan
    EXPLAIN = auto()         # Generate script/visuals for current node
    DEMONSTRATE = auto()     # Synthesize avatar/voice video (calls external service)
    QUESTION = auto()        # Generate and ask question
    EVALUATE = auto()        # Evaluate student response
    ADAPT = auto()           # Decide next action based on evaluation
    CONTINUE = auto()        # Move to next node or end
    DONE = auto()            # Assessment and wrap up
    HUMAN_ESCALATION = auto() # Halted for human intervention
