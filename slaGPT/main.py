# TODO
# prompt should not contain {context}
#
# when asking sources the model does not respond to the checklist

# from typing import List
from operator import itemgetter

from langchain_openai.chat_models import ChatOpenAI

from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableParallel,RunnablePassthrough
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks.base import BaseCallbackHandler
from typing import List,Dict,Any
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    """In memory implementation of chat message history."""

    messages: List[BaseMessage] = Field(default_factory=list)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add a list of messages to the store"""
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []

class myHandler(BaseCallbackHandler):
    # https://stackoverflow.com/questions/77073059/how-can-i-change-from-openai-to-chatopenai-in-langchain-and-flask
    def on_chat_model_start(self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], **kwargs: Any):
        print("myHandler callback started")
        print(messages)
        print("myHandler callback ended")

class slaGPT:
    # is dynamic
    #
    # input     prompt_items        dict
    #           prompt_messages     TODO
    #           vstore              string, vectorestore path
    #           model_name          string, model name 
    def __init__(self,prompt_strings,vstore=None,model_name="gpt-3.5-turbo"):
        self.dctHistory        = {}

        if vstore == "None" or vstore == "none":
            vstore = None
        
        self.model_vstore      = vstore
        self.retriever         = self._init_retriever()

        self.prompt_strings    = prompt_strings
        self.prompt, self.prompt_messages, self.prompt_items  = self._init_prompt()
        
        self.model_name        = model_name
        self.chat_model        = self._init_model()
        self.chat_model_wsrc   = self._init_model_withsources()

        self.callback          = myHandler()

        self.params = {"model name"     : self.model_name,
                       "model vstore"   : self.model_vstore,
                       "prompt_strings" : self.prompt_strings,
                       "prompt_messages": self.prompt_messages,
                       "prompt_items"   : self.prompt_items,
                       "prompt"         : self.prompt}


    def _init_prompt(self):
        # prompt items is anything but input, context or history
        history = self.prompt_strings[1] == 'None' or self.prompt_strings[1] == 'none'
        if not history:
            prompt_messages = [("system", self.prompt_strings[0]),
                            MessagesPlaceholder(variable_name="history"),
                            ("human", self.prompt_strings[2]),
                            ]
        else:
            prompt_messages = [("system", self.prompt_strings[0]),
                            ("human", self.prompt_strings[2]),
                            ]

        prompt_items_key_lst = []
        prompt_items_val_lst = []
        prompt = ChatPromptTemplate.from_messages(prompt_messages)
        prompt_items_key_lst = prompt.input_variables
 
        # remove context, history and input keys if they exist
        for k in ['context','history','input']:
            if k in prompt_items_key_lst:
                prompt_items_key_lst.remove(k)

        #prompt_items = dict(zip(prompt_items_key_lst,prompt_items_val_lst))
        # if val_lst is empty no dict is created
        # a placeholder is created for the prompt_items, assuming the values is set afterwards
        prompt_items = dict.fromkeys(prompt_items_key_lst)
        #print(f"prompt input variables {prompt.input_variables}")
        #print(f"prompt items key list  {prompt_items_key_lst}")
        #print(f"prompt input val lst   {prompt_items_val_lst}")
        #print(f"prompt items {prompt_items}")

        return prompt, prompt_messages, prompt_items


    def _init_retriever(self):
        import os
        
        if self.model_vstore is None:
            # print("WARNING - vstore is None")
            return None
        
        if not (os.path.exists(self.model_vstore)):
            print("WARNING - vstore does not exist")
            return None
        
        # the vectorstore
        vectorstore   = Chroma(embedding_function = OpenAIEmbeddings(),persist_directory = self.model_vstore)

        # the retriever
        search_kwargs = {'k': 4 }
        retriever     = vectorstore.as_retriever(kwargs=search_kwargs)

        return retriever

    def _get_by_session_id(self,session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.dctHistory:
            self.dctHistory[session_id] = InMemoryHistory()
        return self.dctHistory[session_id]
    
    def _format_docs(self,docs):
        return "\n\n".join(doc.page_content for doc in docs)
    
    def _init_model(self):

        llm = ChatOpenAI(model_name  = self.model_name,
                         temperature = 0)
        chain = self.prompt| llm

        # by specifying the keys the Runnable accepts a dict as input
        # you can leave #topic_messages_key   = "topic", out, so that already solves a piece of the puzzle
        chain_with_history = RunnableWithMessageHistory(
            chain,
            self._get_by_session_id,
            input_messages_key   = "input",
            history_messages_key = "history",
        )

        return chain_with_history

    def _init_model_withsources(self):

        if self.model_vstore is None:
            # print("WARNING - vstore is None")
            return None

        llm   = ChatOpenAI(model_name  = self.model_name,temperature = 0)
        chain = self.prompt| llm

        # by specifying the keys the Runnable accepts a dict as input
        # you can leave #topic_messages_key   = "topic", out, so that already solves a piece of the puzzle
        chain_with_history = RunnableWithMessageHistory(
            chain,
            self._get_by_session_id,
            input_messages_key   = "input",
            history_messages_key = "history",
        )

        # this whole dict explanation can be found in sources.doc
        # I f*cking managed to make it dynamic
        
        lstKeys   = []
        lstValues = []
        
        lstKeys   = ["context","input"]
        lstValues = [itemgetter("input") | self.retriever,
                itemgetter("input")]
        
        for k in list(self.prompt_items.keys()):
            lstKeys.append(k)
            lstValues.append(itemgetter(k))

        dictX = dict(zip(lstKeys,lstValues))

        dictY = {
            "context": itemgetter("context"), # This adds the retrieved context as well to the chain
            "response": chain_with_history
        }

        # chain_parallel is a sequence which you will invoke
        # https://python.langchain.com/docs/how_to/dynamic_chain/
        chain_parallel = ( dictX | RunnableParallel (dictY))

        return chain_parallel
    
    def conversation(self,user_question,bSources=False):
        if not bSources:
            return self.conversation_nosources(user_question)
        else:
            return self.conversation_withsources(user_question)

    def conversation_nosources(self,user_question,session_id="foo"):

        # conversation without sources returned
        dctInputData            = self.prompt_items
        dctInputData['input']   = user_question

        if not (self.model_vstore is None):
            retrievedDocs           = self.retriever.invoke(user_question)
            dctInputData['context'] = self._format_docs(retrievedDocs)
            # damn this line caused alot of trouble
            # dctInputData['context'] = self.retriever | self._format_docs
        
        model_output   = self.chat_model.invoke(dctInputData,config={"configurable": {"session_id": session_id}})
        output_message = model_output.content
        output_sources = None

        return output_message, output_sources
    
    def conversation_withsources(self,user_question,session_id="foo"):
        # conversation with sources returned

        if self.model_vstore is None:
            print(f"WARNING - sources were requested but no context supplied")
            return None, None
        
        dctInputData          = self.prompt_items
        dctInputData['input'] = user_question
        
        model_output   = self.chat_model_wsrc.invoke(dctInputData,
                                                     config = {"configurable": {"session_id": session_id}})
        
        # use of a callback to see what prompt is exactly used
        #model_output   = self.chat_model_wsrc.invoke(dctInputData,
        #                                             config = {"configurable": {"session_id": session_id},
        #                                                       "callbacks" : [self.callback]})
        
        output_message = model_output['response'].content
        output_sources = model_output['context']

        return output_message, output_sources
    
    def get_history(self):
        return self.dctHistory
    
    def set_history(self,history):
        self.dctHistory = history

    def get_prompt_items(self):
        return self.prompt_items
    
    def set_prompt_items(self,dctD):
        # copies key value pairs one by one, so that you do not need to specify all in dctD
        # if dctD has an incompatible key the key/value pair is added anyway
        keys_to_copy = list(dctD.keys())
        for k in keys_to_copy:
            self.prompt_items[k] = dctD[k]

    def get_parameters(self):
        return self.params