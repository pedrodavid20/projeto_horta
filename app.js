const express = require('express');
const mysql = require('mysql');
const bodyParser = require('body-parser');

const app = express();
const port = 3000;

const db = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: 'sua_senha',
    database: 'pedidos',
});

db.connect((err) => {
    if (err) {
        console.error('Erro ao conectar ao MySQL:', err);
        return;
    }
    console.log('Conectado ao MySQL.');
});

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

app.post('/realizar_pedido', (req, res) => {
    const { nome, itens, quantidade } = req.body;

    if (!nome || !itens || itens.length === 0) {
        return res.status(400).send('Nome ou itens não fornecidos.');
    }

    const pedidos = [];
    itens.forEach((item) => {
        const quant = quantidade[item] || 1;
        pedidos.push([nome, item, quant]);
    });

    const query = 'INSERT INTO pedidos (nome_cliente, item, quantidade) VALUES ?';
    db.query(query, [pedidos], (err, result) => {
        if (err) {
            console.error('Erro ao inserir no banco:', err);
            return res.status(500).send('Erro ao salvar pedido.');
        }
        console.log('Pedido salvo:', result);
        res.send('Pedido recebido com sucesso!');
    });
});

app.listen(port, () => {
    console.log(`Servidor rodando em http://localhost:${port}`);
});
