import hashlib
from flask import Flask, request, jsonify
import requests
import json
from time import time
from uuid import uuid4
from urllib.parse import urlparse

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.users = []
        self.nodes = set()
        self.new_block(previous_hash=1, proof=100) #create genesis block
        self.create_user(name = 'DMV')
        self.create_user(name = 'DummySeller', cars =[12,32])
        self.create_user(name = 'DummyBuyer')
        self.create_user(name = 'DummyBuyer2')
        self.nodes.add('192.168.1.155:5000')        #add DMV node


    def new_block(self, proof, previous_hash=None, partiesBS = []):    #create new block

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
            'partiesBS': partiesBS,
        }

        self.current_transactions = []          # reset the current list of transactions

        self.chain.append(block)
        return block

    def new_transaction(self, buyerID, sellerID = '', cash = 0, carID = -1):    #creating a new transaction

        self.current_transactions.append({
            'index': len(self.current_transactions),
            'buyerID': buyerID,
            'sellerID': sellerID,
            'cash': cash,
            'carID' : carID,
            'paymentReceived': False,
            'titleReceived': False
        })

        return self.last_block['index'] + 1

    def create_user(self, name, cars = []):                 #creates new users
        user = {
            'index': len(self.users),
            'name': name,
            'cars': cars
        }
        self.users.append(user)
        return user

    def proof_of_work(self, last_proof, sellerID, buyerID, carID):

        proof = sellerID + buyerID + carID
        while self.valid_proof(last_proof, proof) is False:
            proof += sellerID + buyerID + carID

        return proof

    def register_node(self, address):
        self.nodes.add(address)

    def valid_chain(self, chain):

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            if block['previous_hash'] != self.hash(last_block):
                return False

            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def dmv_chain(self):

        new_chain = None
        max_length = len(self.chain)
        response = requests.get(f'http://192.168.1.155:5000/chain')  #get chain from DMV

        if response.status_code == 200:
            length = response.json()['length']
            chain = response.json()['chain']

            if length > max_length and self.valid_chain(chain):
                max_length = length
                new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False

    @staticmethod

    def valid_proof(last_proof, proof):   #check proofing algorithm
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return (guess_hash[:3] == "432")    #return true if hash ends in 432

    def hash(self, block):              #returns hash of block
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


    @property
    def last_block(self):         #returns last block
        return self.chain[-1]



app =  Flask(__name__)

current_user = 0   #change for user
node_identifier = 5000    #change for node

blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    if node_identifier == 5000:
        for transactions in blockchain.current_transactions:
            print(transactions['paymentReceived'] == True)
            print(transactions['titleReceived'] == True)
            if transactions['paymentReceived'] == True and transactions['titleReceived'] == True:
                print('here')
                sellerID = transactions['sellerID']
                buyerID = transactions['buyerID']
                carID = transactions['carID']
                partiesBS = []
                for user in blockchain.users:         #commit the transaction
                    if user['index'] == transactions['sellerID']:
                        user['cars'].remove(transactions['carID'])
                    if user['index'] == transactions['buyerID']:
                        user['cars'].append(transactions['carID'])
            last_block = blockchain.last_block
            last_proof = last_block['proof']
            proof = blockchain.proof_of_work(last_proof, sellerID, buyerID, carID)
            previous_hash = blockchain.hash(last_block)
            partiesBS.append(buyerID)
            partiesBS.append(sellerID)
            block = blockchain.new_block(proof, previous_hash, partiesBS)
            response = {
                'message': "New Block Forged",
                'index': block['index'],
                'transactions': block['transactions'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
            }
            return jsonify(response), 200
    return 'No fulfilled transaction', 400

@app.route('/transactions/new/<buyerID>/<carID>', methods=['Get', 'POST'])
def new_transaction(buyerID,carID):
    for i in range(len(blockchain.users)):
        if blockchain.users[i]['index'] == int(buyerID):         #make sure buyer exists, need to edit to make sure the same transaction doesn't already exist
            index = blockchain.new_transaction(int(buyerID), carID = int(carID))
            response = {'message': f'Transaction will be added to Block {index}'}
            return jsonify(response), 201
    return 'No Buyer with that ID', 400

@app.route('/transactions/update/<sellerID>/<carID>/<cash>', methods=['Get', 'POST'])
def update_transaction(sellerID,carID,cash):  #update transaction with buyer information
    for i in range(len(blockchain.users)):
        if blockchain.users[i]['index'] == int(sellerID):  #make sure seller exists
            if int(carID) in blockchain.users[i]['cars']:             #make sure seller has the car
                for transactions in blockchain.current_transactions:
                    if int(transactions['carID']) == int(carID):      #find transaction related to that car
                        transactions['sellerID'] = int(sellerID)
                        transactions['cash'] = int(cash)
                        response = {'message': f'Transaction updated successfully'}
                        return jsonify(response), 201
    return 'Transaction update failed', 400

@app.route('/transactions/sendcash/<buyerID>/<carID>/<cashAmount>', methods=['Get', 'POST'])
def send_cash(buyerID,carID,cashAmount):  #update transaction paymen received
    for i in range(len(blockchain.users)):
        if blockchain.users[i]['index'] == int(buyerID):  #make sure buyer exists
            for transactions in blockchain.current_transactions:
                if int(transactions['buyerID']) == int(buyerID):  #make sure the buyer is the correct one
                    if int(transactions['carID']) == int(carID):      #make sure its the correct car
                        if int(transactions['cash']) == int(cashAmount) and transactions['paymentReceived'] == False:   #make sure the amount of cash is equal to the buyers request
                            transactions['paymentReceived'] = True
                            response = {'message': f'Transaction updated successfully'}
                            return jsonify(response), 201
    return 'Transaction update failed', 400

@app.route('/transactions/sendtitle/<sellerID>/<carID>', methods=['Get', 'POST'])
def send_title(sellerID,carID):  #update transaction paymen received
    for i in range(len(blockchain.users)):
        if blockchain.users[i]['index'] == int(sellerID):  #make sure buyer exists
            for transactions in blockchain.current_transactions:
                if int(transactions['sellerID']) == int(sellerID):  #make sure the seller is the correct one
                    if int(transactions['carID']) == int(carID) and transactions['titleReceived'] == False:      #make sure its the correct car
                        transactions['titleReceived'] = True
                        response = {'message': f'Transaction updated successfully'}
                        return jsonify(response), 201
    return 'Transaction update failed', 400

@app.route('/chain', methods=['GET'])
def full_chain():                       #returns full chain, up to the latest transactions relative to the current user
    latest_index = 0
    for i in reversed(range(len(blockchain.chain))):
        if current_user in blockchain.chain[i]['partiesBS']:
            latest_index = i
    if node_identifier == 5000:
        latest_index = len(blockchain.chain)
    response = {
        'chain': blockchain.chain[:latest_index+1],
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/users', methods=['GET'])
def all_users():                        #returns a list of all users
    response = {
        'users': blockchain.users,
        'length': len(blockchain.users),
    }
    return jsonify(response), 200

@app.route('/transactions', methods=['GET'])
def all_transactions():                        #returns a list of all current transactions
    response = {
        'transactions': blockchain.current_transactions,
        'length': len(blockchain.current_transactions),
    }
    return jsonify(response), 200

@app.route('/newuser/<newname>', methods=['GET'])
def new_user(newname):
    for i in range(len(blockchain.users)):           #no duplicate users
        if blockchain.users[i]['name'] == newname:
            return 'Already a user', 400
    response = blockchain.create_user(name = newname)
    return jsonify(response), 200

@app.route('/nodes/register/<address>', methods=['GET','POST'])
def register_nodes(address):        #registering nodes
    blockchain.register_node(address)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():           #check dmv for full chain
    replaced = blockchain.dmv_chain()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=node_identifier)
