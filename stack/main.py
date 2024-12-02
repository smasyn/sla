class Stack:
    def __init__(self):
        self.items = []
    
    def isItem(self,item):
        return item in self.items
    
    def isEmpty(self):
        return self.items == []
    
    def push(self,item):
        self.items.append(item)

    def insert(self,idx,item):
        # TODO if idx does not exist
        return self.items.insert(idx,item) 
    
    def pop(self):
        # removes the top of the stack
        return self.items.pop()
    
    def remove(self,item):
        # removes item whatever its position
        self.items.remove(item)
    
    def peek(self):
        # returns top of the stack
        return self.items[len(self.items)-1]
    
    def size(self):
        return len(self.items)
    
    def print(self):
        for i,t in enumerate(self.items):
            print(f"{i}: {t}")
        return '\n'.join(self.items)