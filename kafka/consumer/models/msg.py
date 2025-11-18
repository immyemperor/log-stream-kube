from sqlalchemy.dialects.postgresql import UUID
import uuid
from db_ref import db

class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Text, nullable=False)
    sender_msg_id = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.Text, nullable=False)
    read_at = db.Column(db.Text, nullable=False)
    is_delivered = db.Column(db.Boolean, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False)
    sender_name = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Message {self.id} {self.content}>'
    def to_json(self):
        return {
            "id": self.id,
            "content":self.content,
            "sender_id": self.sender_id,
            "sender_msg_id": self.sender_msg_id,
            "read_at": self.read_at, 
            "created_at":self.created_at,
            "is_read": self.is_read, 
            "is_delivered":self.is_delivered,
            "sender_name":self.sender_name
            }