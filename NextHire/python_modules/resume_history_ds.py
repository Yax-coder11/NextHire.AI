# python_modules/resume_history_ds.py
# Singly Linked List for Resume History (One User → Multiple Resumes)

class ResumeNode:
    def __init__(self, resume_id, created_at, resume_score, readiness_status):
        self.resume_id = resume_id
        self.created_at = created_at
        self.resume_score = resume_score
        self.readiness_status = readiness_status
        self.next = None


class ResumeLinkedList:
    def __init__(self):
        self.head = None

    def add_resume(self, resume_id, created_at, resume_score, readiness_status):
        new_node = ResumeNode(
            resume_id,
            created_at,
            resume_score,
            readiness_status
        )

        if self.head is None:
            self.head = new_node
            return

        current = self.head
        while current.next:
            current = current.next

        current.next = new_node

    def get_resume_history(self):
        history = []
        current = self.head

        while current:
            history.append({
                "resume_id": current.resume_id,
                "created_at": current.created_at,
                "resume_score": current.resume_score,
                "readiness_status": current.readiness_status
            })
            current = current.next

        return history
