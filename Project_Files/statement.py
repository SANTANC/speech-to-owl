from abc import abstractmethod
from dotenv import load_dotenv
load_dotenv()


class Statement:
    def __init__(self, model = None):
        self.model = model

    @abstractmethod
    def generate_data(self):
        pass

    def generate_example(self):
        data= self.generate_data()
        result={"messages": [{"role": "user", "content": self.format(data)}, {"role": "assistant", "content": data}]}

        return result

    @abstractmethod
    def format(self, data):
        pass





