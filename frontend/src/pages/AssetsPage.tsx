import { Container, Typography, Button, Stack } from "@mui/material";

function AssetsPage() {
    return (
        <Container>
            <Stack
                component="div"
                direction="row"
                sx={{ 
                    justifyContent: "space-between", 
                    alignItems: "center", 
                    mt: 4 
                }}
            >
                <Typography variant="h4">Assets</Typography>
                <Button variant="contained">Add Asset</Button>
            </Stack>

        </Container>
    )
}

export default AssetsPage;